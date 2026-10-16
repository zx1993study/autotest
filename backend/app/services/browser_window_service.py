from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe

from web_automation.models import RunConfig

from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.services.agent_task_lease_service import AgentTaskLeaseService


def _fresh(value, seconds):
    try:
        moment = datetime.fromisoformat(str(value or ""))
        return moment.tzinfo is not None and timedelta(0) <= datetime.now(UTC) - moment < timedelta(seconds=seconds)
    except ValueError:
        return False


class BrowserWindowService:
    def __init__(self, repository):
        self.repository = repository

    def _task(self, task_id):
        task = self.repository.get("agent_tasks", task_id)
        if not task:
            raise ResourceNotFoundError("Agent 任务不存在")
        return task

    @staticmethod
    def _headed(task):
        data = task.get("data") or {}
        kind, payload = data.get("task_type"), data.get("payload") or {}
        if kind in {"web_vision_discovery", "web_replay"}:
            return True
        execution = payload.get("execution") or {}
        return kind == "case_execution" and payload.get("case_type") == "WEB" and not RunConfig.from_execution(execution).headless

    def _node(self, task):
        data = task.get("data") or {}
        key = data.get("claimed_by") or data.get("node_key")
        rows, _ = self.repository.list("agent_nodes", page_size=1000)
        return next((n for n in rows if (n.get("data") or {}).get("node_key") == key), {})

    def get(self, task_id):
        task = self._task(task_id)
        data, node = task.get("data") or {}, self._node(task)
        nd = node.get("data") or {}
        window = data.get("browser_window") or {}
        if task.get("status") in {"success", "failed", "canceled"} and window:
            window = {**window, "status": "closed", "phase": "finished"}
        supported = "browser_window_control" in nd.get("capabilities", [])
        online = node.get("status") == "active" and nd.get("agent_status") in {"online", "busy"} and _fresh(nd.get("last_seen_at"), 90)
        command = data.get("browser_window_command") or {}
        if command and not _fresh(command.get("created_at"), 12):
            command = {**command, "status": "expired"} if command.get("status") == "pending" else command
        return {
            "task_id": task_id, "node_name": node.get("name") or nd.get("node_key") or data.get("node_key") or "",
            "node_key": nd.get("node_key") or data.get("node_key") or "", "task_status": task.get("status"),
            "headed": self._headed(task), "supported": supported, "online": online, "window": window,
            "command": {k: command.get(k) for k in ("id", "status", "created_at")},
            "can_show": self._headed(task) and supported and online and task.get("status") == "running"
                        and window.get("status") == "open" and _fresh(data.get("browser_window_seen_at"), 15),
        }

    def request_show(self, task_id):
        current = self.get(task_id)
        if not current["can_show"]:
            raise BusinessRuleError("任务窗口尚未就绪、已关闭或节点不可用")
        task = self._task(task_id)
        previous = (task.get("data") or {}).get("browser_window_command") or {}
        if previous.get("status") == "pending" and _fresh(previous.get("created_at"), 12):
            return {"command_id": previous["id"], "status": "pending"}
        command = {"id": token_urlsafe(18), "window_id": current["window"]["window_id"], "action": "show",
                   "status": "pending", "created_at": datetime.now(UTC).isoformat()}
        if not self.repository.patch_running_agent_task(task_id, task["data"]["claimed_by"], {"browser_window_command": command},
                                                       expected={"browser_window_command": previous}):
            raise BusinessRuleError("窗口控制状态发生变化，请重新显示浏览器")
        return {"command_id": command["id"], "status": "pending"}

    def exchange(self, task_id, payload):
        task = AgentTaskLeaseService(self.repository).owned_task(task_id, payload.node_key, payload.lease_token)
        if task.get("status") != "running" or not self._headed(task):
            raise BusinessRuleError("任务没有运行中的本地有头浏览器")
        data = task.get("data") or {}
        if not data.get("lease_token"):
            raise BusinessRuleError("任务没有有效租约")
        expiry = datetime.fromisoformat(data.get("lease_expires_at") or datetime.now(UTC).isoformat())
        if expiry.tzinfo is None or expiry <= datetime.now(UTC):
            raise BusinessRuleError("任务租约已过期")
        state = payload.window.model_dump()
        old_window = data.get("browser_window") or {}
        if state["revision"] <= old_window.get("revision", 0):
            raise BusinessRuleError("窗口状态已过期")
        patch = {"browser_window": state, "browser_window_seen_at": datetime.now(UTC).isoformat()}
        command = data.get("browser_window_command") or {}
        if command.get("status") == "pending":
            if command.get("window_id") != state["window_id"] or state["status"] != "open":
                command = {**command, "status": "closed"}
            elif not _fresh(command.get("created_at"), 12):
                command = {**command, "status": "expired"}
            elif state.get("command_id") == command.get("id"):
                command = {**command, "status": state["focus"]}
            patch["browser_window_command"] = command
        if not self.repository.patch_running_agent_task(task_id, payload.node_key, patch,
                                                       expected={"browser_window_command": data.get("browser_window_command") or {}, "browser_window": old_window}):
            raise BusinessRuleError("窗口状态发生变化，请重试")
        return {"command": command if command.get("status") == "pending" else None}
