"""Execute one isolated scenario against immutable case/API snapshots."""

import time
from copy import deepcopy

from web_automation.dynamic_values import VARIABLE_NAME, DynamicValueContext

from app.repositories.api_flow_snapshot_repository import ApiFlowSnapshotRepository
from app.scheduler.jobs.api_case_executor import ApiCaseExecutor
from app.services.api_flow_values import (
    EvidenceMask,
    apply_request_override,
    bind_value,
    compare,
    response_value,
    variable_value,
)


class ApiFlowRunner:
    def __init__(self, snapshot, cancel_event, progress=None):
        self.snapshot = snapshot
        self.cancel = cancel_event
        self.progress = progress
        self.executor = ApiCaseExecutor(ApiFlowSnapshotRepository(snapshot["references"]))
        self.scene = snapshot["scenario"]
        self.definition = snapshot["flow"]["data"]
        inputs = {**self.definition["inputs"], **self.scene["data"]["inputs"], **snapshot.get("inputs", {})}
        self.variables = {"global": DynamicValueContext(inputs).resolve(inputs)}
        self.mask = EvidenceMask(snapshot)

    def run(self):
        started = time.perf_counter()
        nodes = self.definition["nodes"]
        positions = {node["key"]: index for index, node in enumerate(nodes)}
        evidence, path = [], []
        index, failed, cancelled = 0, False, False
        self._report(evidence, path, started)
        while index < len(nodes):
            if self.cancel.is_set():
                cancelled = True
                break
            node = nodes[index]
            override = self.scene["data"]["nodes"].get(node["key"], {})
            row, response = self._execute_node(node, override)
            evidence.append(row)
            if row["status"] != "skipped":
                path.append(node["key"])
            if row["status"] == "failed":
                failed = True
                if self.scene["data"]["failure_policy"] == "stop":
                    break
            target = self._next(node, response) if response else "auto"
            row["next"] = target
            self._report(evidence, path, started)
            if target == "end":
                break
            next_index = index + 1 if target == "auto" else positions[target]
            for skipped in nodes[index + 1:next_index]:
                evidence.append(self._skipped(skipped, "未进入此分支"))
            index = next_index
        completed = {row["key"] for row in evidence}
        for node in nodes:
            if node["key"] not in completed:
                evidence.append(self._skipped(node, "已取消" if cancelled else "流程已结束或前置节点失败"))
        expected = self.scene["data"]["expected_end"]
        end_passed = expected == "auto" or (bool(path) and path[-1] == expected)
        status = "cancelled" if cancelled else "failed" if failed or not end_passed else "success"
        result = {"scenario_id": self.scene["id"], "name": self.scene["name"], "status": status,
                  "path": path, "nodes": evidence, "template_version": self.definition["version"],
                  "duration_ms": int((time.perf_counter() - started) * 1000),
                  "expected_end": expected, "end_passed": end_passed,
                  "snapshot": {"flow": self.snapshot["flow"], "scenario": self.scene}, "inputs": self.variables["global"]}
        return self.mask.clean(result)

    def _report(self, evidence, path, started):
        if self.progress:
            self.progress(self.mask.clean({"scenario_id": self.scene["id"], "name": self.scene["name"],
                                          "status": "running", "nodes": evidence, "path": path,
                                          "duration_ms": int((time.perf_counter() - started) * 1000)}))

    def _execute_node(self, node, override):
        try:
            if override.get("mode") == "skip":
                return self._skipped(node, "场景配置为跳过"), None
            if override.get("mode") == "condition":
                condition = override["condition"]
                try:
                    actual = variable_value(self.variables, condition)
                except ValueError:
                    if condition["operator"] != "exists":
                        raise
                    actual = None
                if not compare(actual, condition["operator"], condition.get("value")):
                    return self._skipped(node, "执行条件不满足"), None
            case = deepcopy(self.snapshot["cases"][node["key"]])
            self._apply_request(case, node, override)
            if override.get("assertions") is not None:
                case["assertions"] = override["assertions"]
                case["data"].pop("assertions", None)
            inputs = {key: value for key, value in self.variables["global"].items() if VARIABLE_NAME.fullmatch(key)}
            case["data"]["variables"] = {**(case["data"].get("variables") or {}), **inputs}
            response = {}
            record = self.executor.execute(case, {}, response_capture=response, persist_record=False)
            self.mask.collect(record["data"].get("request", {}))
            row = {"key": node["key"], "name": node["name"], "case_id": case["id"],
                   "status": record["status"], **record["data"]}
            if response.get("status") is not None and row["status"] == "success":
                self._extract(node, override, response, row)
            return row, response
        except Exception as exc:  # noqa: BLE001 - keep one node failure inside its scenario.
            return {"key": node["key"], "name": node["name"], "status": "failed", "error": str(exc)}, None

    def _apply_request(self, case, node, override):
        data = case.setdefault("data", {})
        if isinstance(data.get("request"), dict):
            data.update(data.pop("request"))
        for configured in (node, override):
            apply_request_override(data, configured)
        bindings = override.get("bindings") if override.get("bindings") is not None else node["bindings"]
        if data.get("variables") is None:
            data["variables"] = {}
        for binding in bindings:
            bind_value(data, binding, self.variables)
            if VARIABLE_NAME.fullmatch(binding["name"]):
                data.setdefault("variables", {})[f"bound_{binding['name']}"] = variable_value(self.variables, binding)
        data["skip_auth"] = True
        self.mask.collect(data)

    def _extract(self, node, override, response, row):
        extracts = override.get("extracts") if override.get("extracts") is not None else node["extracts"]
        values = {}
        for extraction in extracts:
            value = response_value(response, extraction)
            missing = value is None or (extraction.get("mode") == "array" and any(item is None for item in value))
            if missing and extraction["required"]:
                row.update(status="failed", error=f"未提取到变量 {extraction['name']}")
                continue
            if value is not None:
                values[extraction["name"]] = value
                if extraction["sensitive"]:
                    self.mask.add(value)
        if row["status"] == "success":
            self.variables[node["key"]] = values
        row["outputs"] = values

    @staticmethod
    def _next(node, response):
        for route in node["routes"]:
            if compare(response_value(response, route), route["operator"], route["value"]):
                return route["target"]
        return node["next"]

    @staticmethod
    def _skipped(node, reason):
        return {"key": node["key"], "name": node["name"], "status": "skipped", "reason": reason}
