import base64
import json
from pathlib import Path

from app.core.exceptions import BusinessRuleError
from app.core.storage import storage_path
from app.schemas.business_generation import GenerationRequest, ReferenceScreenshot
from app.services.business_generation_service import TASKS, BusinessGenerationService
from app.services.generation_candidate_service import safe_context


def check_repair(original, candidate):
    if original.get("input_info", {}) != candidate.get("input_info", {}) or original.get("assertions", []) != candidate.get("assertions", []):
        raise BusinessRuleError("定位修复不能更改输入或断言")
    before, after = original["steps"], candidate["steps"]
    if len(before) != len(after):
        raise BusinessRuleError("定位修复不能删除或新增步骤")
    for old, new in zip(before, after, strict=True):
        if any(old.get(k) != new.get(k) for k in ("action", "value", "expected", "skip")):
            raise BusinessRuleError("定位修复不能改变动作、输入或预期结果")


class GenerationRepairService:
    def __init__(self, repository):
        self.repository = repository
        self.generation = BusinessGenerationService(repository)

    def submit(self, task_id):
        task = self.generation.get(task_id)
        data = task["data"]
        agent = self.repository.get("agent_tasks", data.get("agent_task_id")) if data.get("agent_task_id") else None
        if data.get("domain") != "WEB" or not agent or agent.get("status") != "failed":
            raise BusinessRuleError("当前没有失败的 Web 验证可分析")
        ad = agent["data"]
        original = ad["payload"]["candidate"]
        records = (ad.get("result") or {}).get("records") or []
        failure = (records[0].get("data") or {}) if records else {}
        screenshots = failure.get("screenshots") or []
        references = []
        if screenshots:
            filename = Path(str(screenshots[-1].get("screenshot_file") or "")).name
            path = storage_path("screenshots") / filename
            if filename and path.is_file() and path.stat().st_size <= 4 * 1024 * 1024:
                references = [ReferenceScreenshot(description="失败步骤实际页面截图", image_base64=base64.b64encode(path.read_bytes()).decode())]
        requirement = json.dumps(safe_context({"instruction": "仅修复定位器；保留所有动作、输入和结果断言。鉴权、网络、业务缺陷不应伪装修复，无法确定时返回questions。",
                                              "original": original, "failure": failure.get("error") or ad.get("error"), "timeline": failure.get("step_timeline")}), ensure_ascii=False)
        queued = self.generation.submit("WEB", GenerationRequest(source_id=data["source_id"], model_id=data["model_id"], prompt=requirement, screenshots=references))
        self.repository.update(TASKS, queued["id"], {"data": {**queued["data"], "repair_original": original, "repair_parent_id": task_id}})
        return {"task_id": queued["id"]}

    def finish(self, task):
        ad = task.get("data") or {}
        if ad.get("task_type") != "web_replay":
            return
        task_id = (ad.get("payload") or {}).get("generation_task_id")
        generation = self.repository.get(TASKS, task_id)
        if not generation:
            return
        data = dict(generation["data"])
        if task.get("status") == "failed" and not data.get("failure_knowledge_id"):
            records = (ad.get("result") or {}).get("records") or []
            errors = [safe_context((r.get("data") or {}).get("error")) for r in records]
            from app.services.resource_service import ResourceService

            knowledge = ResourceService("project_knowledge", self.repository).create({
                "name": f"Web 验证失败 - {task_id}", "project_id": generation["project_id"], "status": "active",
                "data": {"domain": "WEB", "kind": "automation_experience", "verification_status": "candidate",
                         "content": json.dumps({"generation_task_id": task_id, "errors": errors}, ensure_ascii=False)},
            })
            self.repository.update(TASKS, task_id, {"data": {**data, "failure_knowledge_id": knowledge["id"]}})
        if task.get("status") == "success" and (data.get("repair_parent_id") or data.get("repair_case_id")):
            parent = self.repository.get(TASKS, data["repair_parent_id"]) or {} if data.get("repair_parent_id") else {}
            knowledge_id = data.get("failure_knowledge_id") or (parent.get("data") or {}).get("failure_knowledge_id")
            knowledge = self.repository.get("project_knowledge", knowledge_id) if knowledge_id else None
            if knowledge:
                from app.services.resource_service import ResourceService

                kd = dict(knowledge["data"])
                kd.update(verification_status="verified", content=json.dumps(safe_context({"cause": kd.get("content"), "verified_locators": [{k: s.get(k) for k in ("name", "locator_type", "locator", "role")} for s in ad["payload"]["candidate"]["steps"]]}), ensure_ascii=False))
                ResourceService("project_knowledge", self.repository).update(knowledge_id, {"data": kd})
