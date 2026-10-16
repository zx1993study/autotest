from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe

from web_automation.discovery.target import is_login_url, matches_target_page

from app.core.exceptions import BusinessRuleError
from app.schemas.agent import AgentTaskCreateRequest
from app.schemas.web_vision_agent import VisionStepRequest
from app.services.agent_node_service import AgentNodeService
from app.services.agent_task_lease_service import AgentTaskLeaseService
from app.services.agent_task_service import AgentTaskService
from app.services.web_target_url_service import resolve_web_target_url
from app.services.web_vision_control_service import WebVisionControlService
from app.services.web_vision_discovery_service import (
    FeatureCapture,
    WebVisionDiscoveryService,
)
from app.utils.vision_images import save_vision_image


class WebVisionAgentService:
    """Local browser capture; AI, credentials and persistence stay on the server."""

    def __init__(self, repository):
        self.repository = repository
        self.discovery = WebVisionDiscoveryService(repository)

    def queue(self, payload, ai_task_id=None):
        page = self.discovery._required_page(payload.page_id)
        if page.get("project_id") != payload.project_id:
            raise BusinessRuleError("页面不属于当前项目")
        model = self.discovery.model_service.active_model(payload.vision_model_id)
        self.discovery._vision_client(int(model["id"]))
        payload = payload.model_copy(update={"vision_model_id": int(model["id"])})
        node_key = self._node(payload.node_key)
        target_url = resolve_web_target_url(self.repository, page)
        if is_login_url(target_url):
            payload = payload.model_copy(update={"wait_for_login": False, "reuse_login": False, "auth_id": None})
        context = {} if is_login_url(target_url) else self._auth_context(payload, page, target_url)
        if context:
            payload = payload.model_copy(update={"auth_id": context["auth_snapshot"]["auth_id"]})
        if ai_task_id:
            previous = self.repository.get("ai_generation_tasks", ai_task_id) or {}
            old_id = (previous.get("data") or {}).get("agent_task_id")
            old = self.repository.get("agent_tasks", old_id) if old_id else None
            if old and old.get("status") in {"pending", "running"}:
                raise BusinessRuleError("该任务已投递本地 Agent，请勿重复提交")
            self.discovery.task_runtime.reset_for_queue(ai_task_id)
        else:
            ai_task_id = self.discovery.submit(payload)["task_id"]
        try:
            task = AgentTaskService(self.repository).create(AgentTaskCreateRequest(
                task_type="web_vision_discovery", node_key=node_key,
                payload={"ai_task_id": ai_task_id, "discovery": payload.model_dump(), "target_url": target_url, "context": context, "window_label": page["name"]},
            ))
            self.discovery.task_runtime.update_task_status(ai_task_id, "queued", {
                "agent_task_id": task["id"], "progress": "等待本地 Agent 启动浏览器",
                "model_id": model["id"], "model_name": (model.get("data") or {}).get("model"),
                "model_http_calls": 0, "login_confirmed": False, "cancel_requested": False,
            })
        except Exception as exc:
            self.discovery.task_runtime.finish_task(ai_task_id, "failed", {"error": str(exc)})
            raise
        return {"task_id": ai_task_id, "agent_task_id": task["id"], "status": "queued", "model_name": (model.get("data") or {}).get("model"), "message": "已投递本地 Agent，有头浏览器将在所选电脑打开"}

    def _node(self, node_key):
        nodes, _ = AgentNodeService(self.repository).list_nodes(1, 1000)
        candidates = []
        for node in nodes:
            data = node.get("data") or {}
            try:
                seen = datetime.fromisoformat(data.get("last_seen_at") or "")
                fresh = seen.tzinfo is not None and datetime.now(UTC) - seen < timedelta(seconds=90)
            except ValueError:
                fresh = False
            if node.get("status") == "active" and fresh and data.get("agent_status") in {"online", "busy"} and "web_vision_discovery" in data.get("capabilities", []):
                candidates.append(node)
        selected = next((n for n in candidates if (n.get("data") or {}).get("node_key") == node_key), None) if node_key else next((n for n in candidates if (n.get("data") or {}).get("default_local_headed")), None)
        if not selected and not node_key and len(candidates) == 1:
            selected = candidates[0]
        if not selected:
            raise BusinessRuleError("没有在线的 Web AI 发现节点，请升级本机 Agent 并启用 Web 能力")
        return selected["data"]["node_key"]

    def _auth_context(self, payload, page, target_url):
        auth_id = payload.auth_id or (page.get("data") or {}).get("auth_id")
        if not auth_id:
            return {}
        auth = self.repository.get("project_auth", int(auth_id))
        if not auth or auth.get("project_id") != payload.project_id:
            raise BusinessRuleError("鉴权配置不属于当前项目")
        return {"auth_snapshot": {"snapshot_id": f"auth_{token_urlsafe(18)}", "auth_id": int(auth_id), "target_url": target_url, "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(), "used_at": ""}}

    def _owned(self, task_id, identity):
        task = AgentTaskLeaseService(self.repository).owned_task(task_id, identity.node_key, identity.lease_token)
        data = task.get("data") or {}
        if task.get("status") != "running" or data.get("task_type") != "web_vision_discovery":
            raise BusinessRuleError("该任务不是执行中的 Web AI 发现任务")
        return task

    def state(self, task_id, identity):
        task = self._owned(task_id, identity)
        ai_id = task["data"]["payload"]["ai_task_id"]
        ai_data = (self.repository.get("ai_generation_tasks", ai_id) or {}).get("data") or {}
        return {**{key: bool(ai_data.get(key)) for key in ("login_confirmed", "cancel_requested")}, "analysis": task["data"].get("vision_job")}

    def interact(self, task_id, action):
        task = AgentTaskService(self.repository).get_task(task_id)
        data = task.get("data") or {}
        if data.get("task_type") == "web_vision_discovery" and action == "cancel":
            return WebVisionControlService(self.repository).cancel(data["payload"]["ai_task_id"])
        if task.get("status") != "running" or data.get("task_type") != "web_vision_discovery" or data.get("vision_phase") != "waiting_login":
            raise BusinessRuleError("任务当前没有等待手动登录")
        ai_id = data["payload"]["ai_task_id"]
        WebVisionControlService(self.repository).check(ai_id)
        self.discovery.task_runtime.update_task_status(ai_id, "running", {"login_confirmed": action == "continue"}, only_if_active=True)
        return {"accepted": True}

    def validate_step(self, task, request):
        raw = task["data"]["payload"]
        WebVisionControlService(self.repository).check(raw["ai_task_id"])
        if request.phase == "overview" and not matches_target_page(raw["target_url"], request.page_url):
            raise BusinessRuleError("实际截图页面与配置地址不一致，已停止分析；请升级 Agent 并检查目标路由")

    def step(self, task_id, request: VisionStepRequest):
        task = self._owned(task_id, request)
        self.validate_step(task, request)
        raw = task["data"]["payload"]
        from app.schemas.ai import WebVisionDiscoveryRequest

        payload = WebVisionDiscoveryRequest.model_validate(raw["discovery"])
        ai_id = int(raw["ai_task_id"])
        if (self.repository.get("ai_generation_tasks", ai_id) or {}).get("status") == "queued":
            self.discovery.task_runtime.reset_for_run(ai_id, only_if_active=True)
        if request.phase == "waiting_login":
            if not payload.wait_for_login:
                raise BusinessRuleError("该任务未启用手动登录")
            self.discovery.task_runtime.update_task_status(ai_id, "running", {"login_confirmed": False}, only_if_active=True)
            self._progress(task, "waiting_login", "仍在登录页，请完成登录后再次点击继续" if request.login_retry else "等待手动登录，请在本地浏览器完成登录后点击继续")
            return {"waiting": True}
        data = task["data"]
        if payload.wait_for_login and not self.state(task_id, request)["login_confirmed"]:
            raise BusinessRuleError("请先确认手动登录完成")
        if request.phase == "overview" and data.get("vision_features") is not None:
            return {"features": data["vision_features"]}
        if request.phase == "captures" and data.get("discovery_result"):
            return data["discovery_result"]
        if request.phase == "captures" and data.get("vision_features") is None:
            raise BusinessRuleError("必须先分析页面截图")
        page = self.discovery._required_page(payload.page_id)
        client = self.discovery._vision_client(payload.vision_model_id)
        client.timeout_sec = None
        self.discovery.last_client = client
        self.discovery.cancel_check = self.discovery.cancel_check or (lambda: WebVisionControlService(self.repository).cancelled(ai_id))
        client.cancel_check = self.discovery.cancel_check
        client.rate_limit_retries = min(client.rate_limit_retries, 1)
        self._progress(task, request.phase, "正在调用视觉模型分析截图")
        try:
            if request.phase == "overview":
                return self._overview(task, request, payload, page, client)
            return self._captures(task, request, payload, page, client)
        except Exception as exc:
            if not client.cancel_check():
                self.discovery.task_runtime.finish_task(ai_id, "failed", {"error": str(exc).replace(client.api_key, "[redacted]"), "model_id": payload.vision_model_id, "model_name": client.model, "model_http_calls": int(data.get("model_http_calls") or 0) + client.requests_made, "execution_mode": "local_headed"}, only_if_active=True)
            raise
        finally:
            self._patch(task_id, {"model_http_calls": int(data.get("model_http_calls") or 0) + client.requests_made})

    def _overview(self, task, request, payload, page, client):
        shot = save_vision_image(task["id"], request.screenshot_base64)
        if not payload.dry_run:
            self.discovery._save_overview(page, shot, request.dom)
        features, warnings = self.discovery._discover_features(client, page, task["data"]["payload"]["target_url"], shot, payload.user_prompt, payload.prompt_template_id)
        features = self.discovery._filter_features(features, payload)
        self.discovery.check_cancelled()
        self.discovery._save_page_features(page, features, payload)
        self._patch(task["id"], {"vision_features": features, "vision_warnings": warnings, "vision_overview": shot})
        return {"features": features}

    def _captures(self, task, request, payload, page, client):
        data = task["data"]
        features = data.get("vision_features") or []
        known = {f"feature_{i}": str(f.get("feature") or "") for i, f in enumerate(features, 1)}
        if len({c.feature_id for c in request.captures}) != len(request.captures) or sum(len(c.screenshot_base64) for c in request.captures) > 28 * 1024 * 1024:
            raise BusinessRuleError("功能截图重复或总大小超过 20 MiB")
        captures = []
        for item in request.captures:
            if known.get(item.feature_id) != item.feature_name:
                raise BusinessRuleError("功能截图不属于本次发现结果")
            # Entry locators are reconstructed from server-approved feature text.
            hint = str(features[int(item.feature_id.split("_")[1]) - 1].get("entry_hint") or item.feature_name)
            entry = None if features[int(item.feature_id.split("_")[1]) - 1].get("capture_mode") == "current_page" else {"name": hint, "text": hint, "type": "button", "action": "click", "locator_type": "text", "locator": hint, "source": "vision_discovery"}
            requests = tuple({"method": r.get("method", "")[:10], "path": r.get("path", "").split("?")[0][:2048]} for r in item.requests)
            captures.append(FeatureCapture(item.feature_id, item.feature_name, save_vision_image(task["id"], item.screenshot_base64), entry, requests, tuple(item.dom)))
        saved, errors = self.discovery._extract_and_save_captures(client, payload, page, captures)
        errors.extend(request.feature_errors)
        result = {"task_type": "web_vision_discovery", "execution_mode": "local_headed", "features": [f.get("feature") for f in features], "saved_features": saved, "saved_elements": sum(s["element_count"] for s in saved), "feature_errors": errors, "warnings": data.get("vision_warnings") or [], "screenshots": [data.get("vision_overview")] + [c.screenshot_path for c in captures], "model_id": payload.vision_model_id, "model_name": client.model, "model_http_calls": int(data.get("model_http_calls") or 0) + client.requests_made, "vision_batches": 1 + int(bool(captures))}
        self._patch(task["id"], {"discovery_result": result, "progress": "截图分析完成"})
        self.discovery.check_cancelled()
        self.discovery.task_runtime.finish_task(data["payload"]["ai_task_id"], "partial_success" if errors else "success", result, only_if_active=True)
        return result

    def _patch(self, task_id, patch):
        task = self.repository.get("agent_tasks", task_id)
        if not self.repository.patch_running_agent_task(task_id, task["data"]["claimed_by"], patch):
            raise BusinessRuleError("任务已结束，无法更新发现进度")

    def _progress(self, task, phase, progress):
        self._patch(task["id"], {"vision_phase": phase, "progress": progress})
        ai_id = task["data"]["payload"]["ai_task_id"]
        self.discovery.task_runtime.update_task_status(ai_id, "running", {"progress": progress}, only_if_active=True)

    def cancel_owned(self, task_id, identity):
        task = self._owned(task_id, identity)
        return WebVisionControlService(self.repository).cancel(task["data"]["payload"]["ai_task_id"])

    def finish(self, task):
        data = task.get("data") or {}
        if data.get("task_type") != "web_vision_discovery":
            return
        ai_id = data["payload"]["ai_task_id"]
        ai = self.repository.get("ai_generation_tasks", ai_id)
        if ai and ai.get("status") not in {"success", "partial_success", "failed", "canceled"}:
            self.discovery.task_runtime.finish_task(ai_id, "failed", {"error": data.get("error") or "本地发现任务未完成", "model_http_calls": data.get("model_http_calls", 0)}, only_if_active=True)

    def active(self, project_id, page_id):
        rows, _ = self.repository.list("ai_generation_tasks", project_id=project_id, page=1, page_size=100, data_filters={"task_type": "web_vision_discovery", "page_id": page_id})
        for row in rows:
            if row.get("status") in {"queued", "running"}:
                data = row.get("data") or {}
                return {"task_id": row["id"], "agent_task_id": data.get("agent_task_id"), "model_name": data.get("model_name"), "status": row["status"]}
        return None
