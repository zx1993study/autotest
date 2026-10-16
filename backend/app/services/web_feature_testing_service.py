from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.schemas.web_features import WebFeatureSave, WebInputParameter
from app.services.generation_candidate_service import (
    candidate_hash,
    has_side_effects,
    safe_context,
    validate_candidate,
)
from app.services.web_page_management_service import WebPageManagementService
from app.services.web_page_service import WebPageResourceService
from app.services.web_input_policy_service import bind_input_steps, normalize_parameters, public_version
from app.services.web_case_secret_service import WebCaseSecretService

VERSIONS = "web_function_versions"


class WebFeatureTestingService:
    def __init__(self, repository):
        self.repository = repository

    def feature(self, feature_id, group_id=None):
        row = self.repository.get("web_pages", feature_id)
        if not row or (group_id is not None and (row.get("data") or {}).get("page_group_id") != group_id):
            raise ResourceNotFoundError("页面功能不存在")
        return row

    def persist_discovery(self, page, capture, output, elements):
        project_id = page["project_id"]
        management = WebPageManagementService(self.repository)
        if not page.get("data", {}).get("page_group_id"):
            management.synchronize_project(project_id)
            page = self.feature(page["id"])
        group_id = page["data"]["page_group_id"]
        from app.services.web_discovery_evidence_service import WebDiscoveryEvidenceService
        from app.services.web_discovery_candidate_service import prepare_discovery

        feature = WebDiscoveryEvidenceService(self.repository).attach(page, capture.feature_name, capture.screenshot_path, getattr(capture, "dom", None))
        parameters = output.get("parameters") or []
        if not parameters:
            types = {"input": "text", "textarea": "textarea", "number": "number", "select": "select", "multi_select": "multiselect", "date": "date", "checkbox": "boolean"}
            for item in elements:
                kind = str(item.get("element_type") or item.get("type") or "")
                if kind in types:
                    parameters.append({"key": f"field_{len(parameters) + 1}", "label": item["name"], "type": types[kind], "required": bool(item.get("required")), "options": item.get("options") or [], "locator": item["name"], "confirmed": False})
        parameters, candidate, warnings = prepare_discovery({**output, "parameters": parameters}, capture)
        inferred_type = next((kind for text, kind in (("新增", "add"), ("编辑", "edit"), ("删除", "delete"), ("导出", "export"), ("登录", "login"), ("查询", "query")) if text in capture.feature_name), "other")
        if not feature:
            feature = self.save_feature(group_id, {"name": capture.feature_name, "feature_type": inferred_type, "parameters": parameters})
        proposal = {"parameters": parameters, "candidate": candidate, "screenshots": [capture.screenshot_path], "api_candidates": safe_context(output.get("api_candidates") or []), "warnings": warnings}
        if proposal["candidate"]:
            try:
                proposal["candidate"] = validate_candidate("WEB", proposal["candidate"], feature)
            except BusinessRuleError as exc:
                proposal["candidate"] = None
                proposal["warnings"].append(str(exc))
        data = dict(feature.get("data") or {})
        # Rediscovery is a proposal, never an overwrite of an established version.
        data["discovery_proposal"] = proposal
        if not data.get("script_version"):
            data.update(parameters=parameters, screenshots=proposal["screenshots"], api_candidates=proposal["api_candidates"])
            if data.get("feature_type") == "other":
                data["feature_type"] = inferred_type
        self.repository.update("web_pages", feature["id"], {"data": data})
        interfaces, _ = self.repository.list("api_interfaces", project_id=project_id, page_size=10000)
        for request in getattr(capture, "requests", ()):
            path = request.get("path") or ""
            matches = [i for i in interfaces if i.get("data", {}).get("method", "").upper() == request.get("method", "").upper() and path.endswith(i.get("data", {}).get("path") or "__missing__")]
            if len(matches) == 1:
                management.create_relations(group_id, [matches[0]["id"]], feature["id"], "network")
        return feature["id"]

    def accept_discovery(self, feature_id):
        feature = self.feature(feature_id)
        proposal = feature.get("data", {}).get("discovery_proposal") or {}
        if not proposal.get("candidate"):
            raise BusinessRuleError("发现结果尚无操作脚本，请补充操作步骤或录制操作")
        version = self.save_version(feature_id, proposal["candidate"], proposal["parameters"], proposal["screenshots"])
        data = dict(self.feature(feature_id)["data"])
        data.pop("discovery_proposal", None)
        self.repository.update("web_pages", feature_id, {"data": data})
        if not self.detail(feature_id)["cases"]:
            self.save_case(feature_id, {"name": proposal["candidate"]["name"], "input_info": proposal["candidate"].get("input_info") or {}})
        return version

    def detail(self, feature_id, group_id=None):
        feature = self.feature(feature_id, group_id)
        data = feature.get("data") or {}
        versions, _ = self.repository.list(VERSIONS, project_id=feature["project_id"], page_size=1000, data_filters={"feature_id": feature_id})
        cases, _ = self.repository.list("web_test_cases", project_id=feature["project_id"], page_size=10000)
        cases = [c for c in cases if c.get("source_id") == feature_id]
        # Old drafts remain reviewable here; loading the workspace never promotes them.
        drafts, _ = self.repository.list("case_drafts", project_id=feature["project_id"], page_size=10000)
        drafts = [d for d in drafts if d.get("source_id") == feature_id and str(d.get("case_type") or (d.get("data") or {}).get("case_type")) == "WEB" and d.get("status") == "draft"]
        group = self.repository.get("web_page_groups", data.get("page_group_id")) if data.get("page_group_id") else None
        interfaces = WebPageManagementService(self.repository).list_interfaces(group["id"], feature_id, None, None, 1, 200)[0] if group else []
        parameters = normalize_parameters(data.get('parameters'))
        return {"feature": feature, "page": group, "parameters": parameters, "versions": [public_version(v) for v in versions],
                "candidate": data.get("candidate"), "screenshots": data.get("discovery_screenshots") or data.get("screenshots") or [], "cases": [WebCaseSecretService.public_case(c) for c in cases], "legacy_drafts": drafts,
                "interfaces": interfaces, "api_candidates": data.get("api_candidates") or []}

    def save_feature(self, group_id, payload, feature_id=None):
        payload = WebFeatureSave.model_validate(payload).model_dump()
        payload['parameters'] = normalize_parameters(payload['parameters'])
        group = WebPageManagementService(self.repository)._required_group(group_id)
        old = self.feature(feature_id, group_id) if feature_id else None
        if old:
            self._not_running(old)
            if payload["expected_revision"] is not None and payload["expected_revision"] != (old.get("data") or {}).get("revision", 0):
                raise BusinessRuleError("功能已更新，请刷新后再保存")
        auth_id = payload.get("auth_id") or (group.get("data") or {}).get("auth_id")
        if auth_id:
            auth = self.repository.get("project_auth", auth_id)
            if not auth or auth.get("project_id") != group["project_id"]:
                raise BusinessRuleError("鉴权必须属于当前项目")
        data = {**(old or {}).get("data", {}), "page_group_id": group_id, "route": group["data"].get("route"),
                "url": group["data"].get("url"), "auth_id": auth_id, "feature_type": payload["feature_type"],
                "parameters": payload["parameters"], "revision": ((old or {}).get("data") or {}).get("revision", 0) + 1}
        values = {"name": payload["name"].strip(), "project_id": group["project_id"], "description": payload["description"], "status": payload["status"], "data": data}
        if not values["name"]:
            raise BusinessRuleError("功能名称不能为空")
        # Validate before writing, so an invalid script cannot partially update metadata.
        candidate = validate_candidate("WEB", payload["candidate"], {"id": feature_id or 0, "data": data}) if payload["candidate"] else None
        saved = WebPageResourceService(self.repository).update(feature_id, values) if old else WebPageResourceService(self.repository).create(values)
        if candidate:
            self.save_version(saved["id"], candidate, parameters=payload["parameters"])
        return self.feature(saved["id"])

    def save_version(self, feature_id, candidate, parameters=None, screenshots=None):
        feature = self.feature(feature_id)
        self._not_running(feature)
        candidate = validate_candidate("WEB", candidate, feature)
        from app.services.web_target_url_service import resolve_web_target_url

        candidate['url'] = resolve_web_target_url(self.repository, feature)
        parameters = parameters if parameters is not None else (feature.get("data") or {}).get("parameters") or self.parameters_from_candidate(candidate)
        parameters = [WebInputParameter.model_validate(p).model_dump() for p in normalize_parameters(parameters)]
        candidate['steps'] = bind_input_steps(candidate['steps'], parameters)
        meta = candidate.get("generation_meta") or {}
        generation = self.repository.get("ai_generation_tasks", meta.get("task_id")) if meta.get("task_id") else None
        gd = (generation or {}).get("data") or {}
        verification_candidate = deepcopy(candidate)
        verification_candidate.pop("generation_meta", None)
        verified_task = self.repository.get("agent_tasks", gd.get("agent_task_id")) if gd.get("agent_task_id") else None
        verified = bool(generation and gd.get("source_id") == feature_id and gd.get("verified_hash") == candidate_hash(verification_candidate) and verified_task and verified_task.get("status") == "success")
        version = self.repository.create(VERSIONS, {"name": candidate["name"], "project_id": feature["project_id"], "status": "verified" if verified else "draft",
            "data": {"feature_id": feature_id, "candidate": candidate, "parameters": parameters, "created_at": datetime.now(UTC).isoformat()}})
        data = {**feature.get("data", {}), "candidate": candidate, "parameters": parameters, "script_version": version["id"],
                "script_status": version["status"], "revision": (feature.get("data") or {}).get("revision", 0) + 1}
        if screenshots is not None:
            data["screenshots"] = screenshots
        self.repository.update("web_pages", feature_id, {"data": data})
        return version

    @staticmethod
    def parameters_from_candidate(candidate):
        inputs = candidate.get("input_info") or {}
        steps = candidate.get("steps") or []
        result = []
        for key, value in inputs.items():
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
                continue
            step = next((s for s in steps if s.get("value") == "{{" + key + "}}"), {})
            kind = {'select':'select','multi_select':'multiselect','check':'boolean','uncheck':'boolean'}.get(step.get('action'), 'text')
            result.append({"key": key, "label": step.get("name") or step.get("locator") or key, "type": kind,
                "required": False, "default_value": value, "locator_type": step.get("locator_type") or "label", "locator": step.get("locator") or "", "confirmed": False})
        for index, step in enumerate(steps, 1):
            if step.get('action') == 'manual':
                result.append({'key':f'manual_{index}','label':str(step.get('name') or step.get('locator') or '人工输入')[:128], 'type':'manual', 'required':False, 'required_known':False,
                               'locator_type':step.get('locator_type') or 'label','locator':step.get('locator') or '', 'frame_selector':step.get('frame_selector') or '', 'confirmed':False})
        return normalize_parameters(result)

    def activate_version(self, feature_id, version_id):
        feature = self.feature(feature_id)
        self._not_running(feature)
        version = self.repository.get(VERSIONS, version_id)
        if not version or version.get("project_id") != feature["project_id"] or version["data"].get("feature_id") != feature_id:
            raise BusinessRuleError("脚本版本不属于当前功能")
        data = {**feature["data"], "candidate": version["data"]["candidate"], "parameters": version["data"]["parameters"],
                "script_version": version_id, "script_status": version["status"], "revision": feature["data"].get("revision", 0) + 1}
        self.repository.update("web_pages", feature_id, {"data": data})
        return self.detail(feature_id)

    def delete_feature(self, feature_id):
        feature = self.feature(feature_id)
        self._not_running(feature)
        for table in ("web_test_cases", "case_drafts", VERSIONS, "web_page_api_relations", "web_elements"):
            rows, _ = self.repository.list(table, project_id=feature["project_id"], page_size=10000)
            ids = [r["id"] for r in rows if (r.get("source_id") == feature_id and (table != "case_drafts" or str(r.get("case_type") or r.get("data", {}).get("case_type")) == "WEB")) or (r.get("data") or {}).get("feature_id") == feature_id or (table == "web_elements" and r.get("data", {}).get("page_id") == feature_id)]
            self.repository.batch_delete(table, ids)
        return self.repository.delete("web_pages", feature_id)

    def save_case(self, feature_id, payload, case_id=None):
        feature = self.feature(feature_id)
        self._not_running(feature)
        old = self._case(feature_id, case_id) if case_id else None
        copy_source = self._case(feature_id, payload['copy_from_case_id']) if payload.get('copy_from_case_id') else None
        data = feature.get("data") or {}
        version_id = payload.get("script_version") or data.get("script_version")
        version = self.repository.get(VERSIONS, version_id) if version_id else None
        if version_id and (not version or version["data"].get("feature_id") != feature_id or version.get("project_id") != feature["project_id"]):
            raise BusinessRuleError("用例脚本版本不属于当前功能")
        candidate = deepcopy((version or {}).get("data", {}).get("candidate") or data.get("candidate") or {})
        parameters = normalize_parameters(version["data"].get("parameters", []) if version else data.get("parameters"))
        defaults = {} if payload.get("allow_invalid_inputs") else {p["key"]: p["default_value"] for p in parameters if p.get("type") not in {"manual", "password"} and p.get("default_value") is not None}
        inputs = {**defaults, **(payload.get("input_info") or {})}
        self._check_inputs(parameters, inputs, validate_required=False)
        protected = WebCaseSecretService(self.repository).protect(parameters, inputs, ((old or copy_source or {}).get('data') or {}).get('secret_inputs'))
        expected = payload.get("expected_steps") or []
        if any(s.get("action") != "assert" for s in expected):
            raise BusinessRuleError("用例预期结果只能包含 assert 步骤")
        steps = candidate.get("steps") or (old or {}).get("steps") or []
        steps = bind_input_steps(steps, parameters)
        inactive = [p for p in parameters if p.get("condition") and inputs.get(p["condition"].get("key")) != p["condition"].get("equals")]
        input_actions = {"fill", "select", "multi_select", "check", "uncheck"}
        # Hidden conditional fields must not be located or filled during replay.
        steps = [s for s in steps if s.get("action") not in input_actions or not any(
            s.get("value") == "{{" + p["key"] + "}}" or (p.get("locator") and s.get("locator") == p["locator"] and s.get("locator_type") == p.get("locator_type", "label"))
            for p in inactive)]
        for step in steps:
            parameter = next((p for p in parameters if p.get('type') == 'manual' and (step.get('value') == '{{' + p['key'] + '}}' or (p.get('locator') and p['locator'] == step.get('locator') and p.get('locator_type') == step.get('locator_type')))), None)
            if parameter:
                step.update(action='manual', frame_selector=parameter.get('frame_selector') or '')
                step.pop('value', None)
            match = re.fullmatch(r"\{\{([A-Za-z_][A-Za-z0-9_]*)\}\}", str(step.get("value") or ""))
            if match and isinstance(inputs.get(match[1]), bool) and step.get("action") in {"check", "uncheck"}:
                step["action"] = "check" if inputs[match[1]] else "uncheck"
            if match and match[1] not in inputs and match[1] not in protected and not step.get('sensitive') and step.get("action") == "fill" and any(p["key"] == match[1] for p in parameters):
                step["value"] = ""
        if expected:
            steps = [s for s in steps if s.get("action") != "assert"] + expected
        if steps:
            normalized = validate_candidate("WEB", {"name": payload["name"], "steps": deepcopy(steps), "input_info": inputs}, {**feature, 'data':{**data, 'parameters':parameters}})
            steps = normalized["steps"]
        variables = {k: v for k, v in candidate.get("variables", {}).items() if k not in {p["key"] for p in parameters}}
        request = {**candidate, "name": payload["name"], "steps": steps, "input_info": inputs, "variables": {**variables, **inputs}}
        case_data = {**(old or {}).get("data", {}), "request": request, "variables": request["variables"], "input_info": inputs, "script_version": version_id,
                     "allow_invalid_inputs": bool(payload.get("allow_invalid_inputs")), "expected_steps": expected,
                     "feature_revision": data.get("revision", 0), "auth_id": data.get("auth_id"), "case_type": "WEB", 'secret_inputs':protected, 'secret_keys':list(protected)}
        values = {"name": payload["name"], "project_id": feature["project_id"], "source_id": feature_id, "case_type": "WEB",
                  "priority": payload.get("priority", "P2"), "status": payload.get("status", "active"), "data": case_data,
                  "steps": steps, "assertions": candidate.get("assertions") or []}
        saved = self.repository.update("web_test_cases", case_id, values) if old else self.repository.create("web_test_cases", values)
        return WebCaseSecretService.public_case(saved)

    def delete_case(self, feature_id, case_id):
        self._not_running(self.feature(feature_id))
        self._case(feature_id, case_id)
        return self.repository.delete("web_test_cases", case_id)

    def import_draft(self, feature_id, draft_id):
        feature = self.feature(feature_id)
        self._not_running(feature)
        draft = next((d for d in self.detail(feature_id)["legacy_drafts"] if d["id"] == draft_id), None)
        if not draft:
            raise ResourceNotFoundError("待导入用例不存在")
        from app.services.case_draft_service import CaseDraftService

        return CaseDraftService("WEB", self.repository).accept(draft_id)

    def run(self, feature_id, payload):
        feature = self.feature(feature_id)
        if feature.get("status") != "active":
            raise BusinessRuleError("功能已停用")
        cases = [self._case(feature_id, cid) for cid in dict.fromkeys(payload["case_ids"])]
        for case in cases:
            if case.get("status") != "active":
                raise BusinessRuleError("所选用例已停用")
            version_id = (case.get("data") or {}).get("script_version")
            version = self.repository.get(VERSIONS, version_id) if version_id else None
            parameters = normalize_parameters(version["data"].get("parameters", []) if version else feature.get("data", {}).get("parameters"))
            if payload.get("headless") and any(s.get("action") == "manual" for s in case.get("steps") or []):
                raise BusinessRuleError("此用例需要人工输入，请选择本地有头执行")
            values = {**((case.get('data') or {}).get('input_info') or {}), **WebCaseSecretService(self.repository).reveal(case.get('data', {}).get('secret_inputs'))}
            self._check_inputs(parameters, values, validate_required=not case.get("data", {}).get("allow_invalid_inputs"))
            if any(s.get('sensitive') and s.get('input_key') not in values for s in case.get('steps') or []):
                raise BusinessRuleError('请编辑用例并填写密码，保存后再执行')
            candidate = {"name": case["name"], "steps": case.get("steps") or [], "input_info": case.get("data", {}).get("input_info") or {}}
            validate_candidate("WEB", candidate, feature)
            if has_side_effects(candidate) and not payload.get("approve_side_effects"):
                raise BusinessRuleError("请确认允许用例中的点击、填写和提交操作")
        from app.services.agent_node_service import AgentNodeService
        from app.services.agent_task_service import AgentTaskService

        nodes, _ = AgentNodeService(self.repository).list_nodes(1, 1000)
        node = next((n for n in nodes if n.get("data", {}).get("node_key") == payload["node_key"]), None)
        nd = (node or {}).get("data") or {}
        if any(c.get('data', {}).get('secret_inputs') for c in cases) and 'web_secret_inputs' not in nd.get('capabilities', []):
            raise BusinessRuleError('加密密码执行需要升级到 0.3.8 或更新的 Web Agent')
        if any(s.get('action') == 'manual' for c in cases for s in c.get('steps') or []) and 'web_recording' not in nd.get('capabilities', []):
            raise BusinessRuleError('人工输入需要升级到 0.3.7 或更新的 Web Agent')
        try:
            fresh = 0 <= (datetime.now(UTC) - datetime.fromisoformat(nd.get("last_seen_at", ""))).total_seconds() < 90
        except (ValueError, TypeError):
            fresh = False
        if not node or node.get("status") != "active" or not fresh or nd.get("agent_status") not in {"online", "busy"} or "case_execution" not in nd.get("capabilities", []):
            raise BusinessRuleError("请选择在线且支持 Web 执行的 Agent")
        task = AgentTaskService(self.repository).create_case_execution_task("WEB", {
            "case_ids": [c["id"] for c in cases], "project_id": feature["project_id"], "node_id": payload["node_key"],
            "skip_auth": feature.get('data', {}).get('feature_type') == 'login',
            "mode": "remote_node" if payload["headless"] else "local_headed",
            "config": {"engine": "playwright", "headless": payload["headless"], "record_video": payload.get("record_video", True), "max_ai_calls_per_case": 0}})
        return {"agent_task_id": task["id"], "status": task["status"]}

    def repair(self, feature_id, payload):
        feature = self.feature(feature_id)
        case = self._case(feature_id, payload["case_id"])
        task = self.repository.get("agent_tasks", payload["agent_task_id"])
        ad = (task or {}).get("data") or {}
        snapshot = next((c for c in ad.get("payload", {}).get("cases", []) if c["id"] == case["id"] and c.get("source_id") == feature_id and c.get("project_id") == feature["project_id"]), None)
        if not snapshot or task.get("status") != "failed":
            raise BusinessRuleError("只能分析当前功能失败任务中的用例")
        records = (ad.get("result") or {}).get("records") or []
        record = next((r for r in records if (r.get("data") or {}).get("case_id") == case["id"] and r.get("status") == "failed"), None)
        if not record:
            raise BusinessRuleError("该用例没有失败执行记录")
        failure = record.get("data") or {}
        original = {"name": case["name"], "steps": snapshot.get("steps") or [], "input_info": snapshot.get("data", {}).get("input_info") or {}, "assertions": snapshot.get("assertions") or []}
        import base64

        from app.core.storage import storage_path
        from app.schemas.business_generation import (
            GenerationRequest,
            ReferenceScreenshot,
        )
        from app.services.business_generation_service import BusinessGenerationService

        requirement = json.dumps(safe_context({"instruction": "先分类为脚本、鉴权、环境、输入或业务缺陷。仅修复定位器，不改变动作、输入和结果断言。不确定或非脚本问题返回questions，禁止削弱断言。", "original": original, "failure": {"error": failure.get("error"), "events": failure.get("events"), "step_count": failure.get("step_count")}}), ensure_ascii=False)
        references = []
        screenshots = failure.get("screenshots") or []
        if screenshots:
            filename = Path(str(screenshots[-1].get("screenshot_file") or "")).name
            path = storage_path("screenshots") / filename
            if filename and path.is_file() and path.stat().st_size <= 4 * 1024 * 1024:
                references = [ReferenceScreenshot(description="失败步骤截图", image_base64=base64.b64encode(path.read_bytes()).decode())]
        queued = BusinessGenerationService(self.repository).submit("WEB", GenerationRequest(source_id=feature_id, prompt=requirement, screenshots=references))
        knowledge = self.repository.create("project_knowledge", {"name": f"Web 功能失败分析 #{task['id']}", "project_id": feature["project_id"], "status": "active",
            "data": {"domain": "WEB", "kind": "automation_experience", "verification_status": "candidate", "content": requirement, "feature_id": feature_id, "agent_task_id": task["id"]}})
        version_id = snapshot.get("data", {}).get("script_version")
        version = self.repository.get(VERSIONS, version_id) if version_id else None
        parameters = version.get("data", {}).get("parameters", []) if version else feature.get("data", {}).get("parameters", [])
        self.repository.update("ai_generation_tasks", queued["id"], {"data": {**queued["data"], "repair_original": original, "failure_knowledge_id": knowledge["id"], "repair_case_id": case["id"], "repair_parameters": parameters}})
        return {"task_id": queued["id"]}

    def finish(self, task):
        data = task.get("data") or {}
        if data.get("task_type") != "case_execution" or data.get("payload", {}).get("case_type") != "WEB":
            return
        snapshots = {c["id"]: c for c in data["payload"].get("cases", [])}
        for record in (data.get("result") or {}).get("records", []):
            if record.get("status") != "success":
                continue
            snapshot = snapshots.get(record.get("data", {}).get("case_id")) or {}
            version_id = snapshot.get("data", {}).get("script_version")
            version = self.repository.get(VERSIONS, version_id) if version_id else None
            if not version or version["data"].get("feature_id") != snapshot.get("source_id") or version["project_id"] != snapshot.get("project_id") or version["data"]["candidate"]["steps"] != snapshot.get("steps"):
                continue
            self.repository.update(VERSIONS, version_id, {"status": "verified"})
            feature = self.repository.get("web_pages", snapshot["source_id"])
            if feature and feature["data"].get("script_version") == version_id:
                self.repository.update("web_pages", feature["id"], {"data": {**feature["data"], "script_status": "verified"}})

    def _case(self, feature_id, case_id):
        feature = self.feature(feature_id)
        case = self.repository.get("web_test_cases", case_id)
        if not case or case.get("source_id") != feature_id or case.get("project_id") != feature["project_id"]:
            raise ResourceNotFoundError("输入用例不属于当前功能")
        return case

    def _not_running(self, feature):
        tasks, _ = self.repository.list("agent_tasks", page_size=10000)
        for task in tasks:
            if task.get("status") not in {"pending", "running"}:
                continue
            payload = (task.get("data") or {}).get("payload") or {}
            if any(c.get("source_id") == feature["id"] and c.get("project_id") == feature["project_id"] for c in payload.get("cases", [])) or (payload.get("source_id") == feature["id"] and payload.get("project_id") == feature["project_id"]) or (payload.get("discovery", {}).get("page_id") == feature["id"] and payload.get("discovery", {}).get("project_id") == feature["project_id"]):
                raise BusinessRuleError("功能正在执行，请等待结束后修改或删除")

    @staticmethod
    def _check_inputs(parameters, values, validate_required):
        for p in parameters:
            condition = p.get("condition") or {}
            if condition and values.get(condition.get("key")) != condition.get("equals"):
                continue
            value = values.get(p["key"], p.get("default_value"))
            if p.get("type") == "manual" and value not in (None, ""):
                raise BusinessRuleError("人工输入不可保存到用例")
            if p.get('type') == 'manual':
                continue
            if validate_required and p.get("required") and value in (None, "", []):
                raise BusinessRuleError(f"请补充必填参数：{p['label']}")
            if not validate_required or value in (None, "", []) or (isinstance(value, str) and "{{" in value):
                continue
            if p.get("type") == "number" and (not isinstance(value, (int, float)) or isinstance(value, bool)):
                raise BusinessRuleError(f"{p['label']} 必须为数字")
            if p.get("type") == "boolean" and not isinstance(value, bool):
                raise BusinessRuleError(f"{p['label']} 必须为布尔值")
            if p.get("type") == "multiselect" and not isinstance(value, list):
                raise BusinessRuleError(f"{p['label']} 必须为多选数组")
            if p.get("type") in {"select", "multiselect"} and p.get("options"):
                allowed = [o.get("value") if isinstance(o, dict) else o for o in p["options"]]
                selected = value if isinstance(value, list) else [value]
                if any(v not in allowed for v in selected):
                    raise BusinessRuleError(f"{p['label']} 不在有效选项中")
            if p.get("type") in {"date", "datetime"}:
                try:
                    datetime.fromisoformat(str(value))
                except ValueError as exc:
                    raise BusinessRuleError(f"{p['label']} 日期格式无效") from exc
            rules = p.get("validation") or {}
            if rules.get("min_length") is not None and len(str(value)) < int(rules["min_length"]):
                raise BusinessRuleError(f"{p['label']} 长度不足")
            if rules.get("max_length") is not None and len(str(value)) > int(rules["max_length"]):
                raise BusinessRuleError(f"{p['label']} 超过长度限制")
            if isinstance(value, (int, float)):
                if rules.get("min") is not None and value < float(rules["min"]):
                    raise BusinessRuleError(f"{p['label']} 小于最小值")
                if rules.get("max") is not None and value > float(rules["max"]):
                    raise BusinessRuleError(f"{p['label']} 超过最大值")
