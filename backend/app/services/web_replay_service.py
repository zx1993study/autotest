from datetime import UTC, datetime
from urllib.parse import urlparse

from app.core.exceptions import BusinessRuleError
from app.enums.business import AgentTaskTypeEnum
from app.schemas.agent import AgentTaskCreateRequest
from app.services.agent_task_lease_service import AgentTaskLeaseService
from app.services.agent_task_service import AgentTaskService
from app.services.business_generation_service import TASKS, BusinessGenerationService
from app.services.generation_candidate_service import (
    candidate_hash,
    has_side_effects,
    validate_candidate,
)


class WebReplayService:
    def __init__(self, repository):
        self.repository = repository
        self.generation = BusinessGenerationService(repository)

    def queue(self, task_id, payload):
        task = self.generation.get(task_id)
        data = dict(task["data"])
        if task["status"] != "success" or data.get("domain") != "WEB" or data.get("saved_resource"):
            raise BusinessRuleError("只能验证尚未保存的 Web 候选")
        previous = self.repository.get("agent_tasks", data.get("agent_task_id")) if data.get("agent_task_id") else None
        if previous and previous["status"] in {"pending", "running"}:
            raise BusinessRuleError("该候选正在验证")
        source = self.generation.source("WEB", data["source_id"])
        candidate = validate_candidate("WEB", payload.candidate, source)
        protected_cases = []
        if any(s.get('sensitive') for s in candidate['steps']):
            original = self.repository.get('web_test_cases', data.get('repair_case_id')) if data.get('repair_case_id') else None
            if not original or original.get('source_id') != source['id'] or original.get('project_id') != task['project_id'] or not original.get('data', {}).get('secret_inputs'):
                raise BusinessRuleError('含密码的候选请先保存脚本，再在输入用例中设置密码并执行')
            protected_cases = [original]
        if data.get("repair_original"):
            from app.services.generation_repair_service import check_repair

            check_repair(data["repair_original"], candidate)
        if has_side_effects(candidate) and not payload.approve_side_effects:
            raise BusinessRuleError("包含会改变页面或业务状态的操作，请明确确认后验证")
        nodes, _ = self.repository.list("agent_nodes", page_size=1000)
        node = next((n for n in nodes if (n.get("data") or {}).get("node_key") == payload.node_key), None)
        nd = (node or {}).get("data") or {}
        if protected_cases and 'web_secret_inputs' not in nd.get('capabilities', []):
            raise BusinessRuleError('密码用例修复验证需要升级到 0.3.8 或更新的 Agent')
        if any(s.get('action') == 'manual' for s in candidate['steps']) and 'web_recording' not in nd.get('capabilities', []):
            raise BusinessRuleError('人工输入需要升级到 0.3.7 或更新的 Web Agent')
        try:
            fresh = (datetime.now(UTC) - datetime.fromisoformat(nd.get("last_seen_at", ""))).total_seconds() < 90
        except (ValueError, TypeError):
            fresh = False
        if not node or node.get("status") != "active" or not fresh or nd.get("agent_status") not in {"online", "busy"} or "web_replay" not in nd.get("capabilities", []):
            raise BusinessRuleError("请选择在线且已升级支持截图复现的 Agent")
        from app.services.web_target_url_service import resolve_web_target_url
        from web_automation.discovery.target import is_login_url

        url = resolve_web_target_url(self.repository, source)
        if urlparse(url).scheme not in {"http", "https"} or not urlparse(url).hostname:
            raise BusinessRuleError("当前 Web 页面必须配置完整 HTTP(S) 地址")
        agent = AgentTaskService(self.repository).create(AgentTaskCreateRequest(
            task_type=AgentTaskTypeEnum.WEB_REPLAY, node_key=payload.node_key,
            payload={"generation_task_id": task_id, "project_id": task["project_id"], "source_id": source["id"],
                     "candidate": candidate, "target_url": url, "wait_for_login": payload.wait_for_login and not is_login_url(url),
                     **({'case_type':'WEB','cases':protected_cases} if protected_cases else {})},
        ))
        data.update(agent_task_id=agent["id"], verified_hash=candidate_hash(candidate), progress="等待本地浏览器验证")
        self.repository.update(TASKS, task_id, {"data": data})
        return {"agent_task_id": agent["id"]}

    def control(self, task_id, action):
        task = self.generation.get(task_id)
        data = dict(task["data"])
        if data.get("task_type") != "business_generation":
            raise BusinessRuleError("请在 Web 发现流程中控制该任务")
        if action == "cancel" and task["status"] in {"queued", "running"}:
            return self.repository.update_if_status(TASKS, task_id, task["status"], {"status": "canceled"})
        agent_id = data.get("agent_task_id")
        agent = self.repository.get("agent_tasks", agent_id) if agent_id else None
        if not agent or agent["status"] not in {"pending", "running"}:
            raise BusinessRuleError("当前没有可控制的验证任务")
        ad = dict(agent["data"])
        if action == "continue" and ad.get("replay_phase") != "waiting_login":
            raise BusinessRuleError("任务不在等待登录状态")
        ad["login_confirmed" if action == "continue" else "cancel_requested"] = True
        return self.repository.update("agent_tasks", agent_id, {"data": ad})

    def state(self, task_id, payload):
        task = AgentTaskLeaseService(self.repository).owned_task(task_id, payload.node_key, payload.lease_token)
        data = task.get("data") or {}
        if task["status"] != "running" or data.get("task_type") != "web_replay":
            raise BusinessRuleError("任务不在验证中")
        if payload.phase != "state":
            self.repository.patch_running_agent_task(task_id, payload.node_key, {"replay_phase": payload.phase})
        return {"login_confirmed": bool(data.get("login_confirmed")), "cancel_requested": bool(data.get("cancel_requested"))}
