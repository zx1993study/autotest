from __future__ import annotations

import base64
import time
import uuid
from pathlib import Path
from typing import Any

from agent_app.executors.screen_video import ScreenVideo
from agent_app.executors.wda_actions import WdaActions
from agent_app.executors.wda_sessions import WdaSessionPool


class LocalMobileCaseExecutor:
    def __init__(self, artifacts_dir: Path, pool=None) -> None:
        self.artifacts_dir = artifacts_dir
        self.pool = pool or WdaSessionPool(artifacts_dir)

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        records = [self._case(case, payload) for case in payload.get("cases", [])]
        failed = sum(record["status"] == "failed" for record in records)
        return {"total": len(records), "failed_count": failed, "success_count": len(records) - failed, "records": records}

    def _case(self, case, payload):
        from web_automation.dynamic_values import prepare_dynamic_execution

        started = time.monotonic()
        context = payload.get("context") or {}
        execution = payload.get("execution") or {}
        case, execution, dynamic = prepare_dynamic_execution(case, execution)
        data = case.get("data") or {}
        device = context.get("device") or (execution.get("config") or {}).get("device") or {}
        bundle_id = str(context.get("bundle_id") or data.get("bundle_id") or "")
        timeline, screenshots = [], []
        result = {"case_type": "APP", "case_id": case.get("id"), "scenario_id": context.get("scenario_id"), "run_id": context.get("run_id"), "device_id": device.get("id"), "device_name": device.get("name"), "input_snapshot": data.get("input_info", {}), "dynamic_values": dynamic.snapshot(), "step_timeline": timeline, "screenshots": screenshots}
        error = ""
        try:
            self._steps(case)
            with self.pool.connect(device, bundle_id, bool(data.get("start_from_current_screen", True))) as (session, reused):
                result["session_reused"] = reused
                result.update(self._execute_steps(session, case, execution, timeline, screenshots))
        except Exception as exc:  # noqa: BLE001 - SDK failures must become execution evidence.
            error = str(exc)
        result.update(data.pop("_recording_evidence", {}))
        result.update({"error": error, "duration_ms": round((time.monotonic() - started) * 1000)})
        if screenshots:
            result["screenshot_file"] = screenshots[-1].get("screenshot_file")
        return {"name": f"APP - {case.get('name') or 'Scenario'}", "project_id": case.get("project_id"), "status": "failed" if error else "success", "description": error or None, "data": result}

    def _execute_steps(self, session, case, execution, timeline, screenshots):
        data = case.get("data") or {}
        steps = self._steps(case)
        recorder = None
        if (execution.get("config") or {}).get("record_video", data.get("record_video", True)):
            recorder = ScreenVideo(session, self.artifacts_dir / "videos" / f"{uuid.uuid4().hex}.mp4")
            recorder.start()
        try:
            actions = WdaActions(session)
            for index, step in enumerate(steps, 1):
                self._step(actions, step, index, timeline, screenshots)
            for assertion in case.get("assertions") or data.get("assertions") or []:
                if any(item.get("name") == assertion.get("step") and str(item.get("action") or "").startswith("assert") and item.get("status") == "success" for item in timeline):
                    continue
                if assertion.get("type") not in {"text_contains", "screen_contains"}:
                    raise ValueError(f"不支持的断言类型：{assertion.get('type')}")
                self._step(actions, {"name": assertion.get("step") or "结果断言", "action": "assert_screen_contains", "expected": assertion.get("expected")}, len(timeline) + 1, timeline, screenshots)
        finally:
            self._screenshot(session, screenshots)
            recording = recorder.stop() if recorder else {}
            data["_recording_evidence"] = recording
        return recording

    @staticmethod
    def _steps(case):
        data = case.get("data") or {}
        steps = case.get("steps") or data.get("steps") or []
        if data.get("script_path"):
            raise ValueError("请将旧本地脚本转换为结构化步骤后执行")
        if not steps:
            raise ValueError("场景没有可执行步骤")
        if not isinstance(steps, list) or any(not isinstance(step, dict) for step in steps):
            raise ValueError("操作步骤必须是对象列表")
        return steps

    def _step(self, actions, step, index, timeline, screenshots):
        started = time.monotonic()
        item = {"index": index, "name": step.get("name"), "action": step.get("action"), "status": "running"}
        timeline.append(item)
        try:
            actions.run(step)
            item["status"] = "success"
        except Exception as exc:
            item.update({"status": "failed", "error": str(exc), "outcome_unknown": step.get("action") in {"tap", "click", "input", "select"}})
            raise
        finally:
            item["duration_ms"] = round((time.monotonic() - started) * 1000)
            if step.get("take_screenshot") or item["status"] == "failed":
                self._screenshot(actions.session, screenshots)

    def _screenshot(self, session, screenshots):
        try:
            path = self.artifacts_dir / "screenshots" / f"{uuid.uuid4().hex}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            session.screenshot(str(path))
            raw = path.read_bytes()
            if len(raw) <= 10 * 1024 * 1024:
                screenshots.append({"screenshot_file": path.name, "screenshot_base64": base64.b64encode(raw).decode("ascii")})
        except Exception as exc:  # noqa: BLE001 - screenshots must not mask the original failure.
            screenshots.append({"screenshot_error": str(exc)})
