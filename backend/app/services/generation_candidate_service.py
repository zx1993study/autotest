import hashlib
import json
import re
from copy import deepcopy
from typing import Any

from app.core.exceptions import BusinessRuleError

WEB_ACTIONS = {"click", "fill", "select", "multi_select", "check", "uncheck", "hover", "assert", "wait", "manual"}
LOCATORS = {"role", "label", "testid", "placeholder", "text", "css", "xpath"}
SENSITIVE_KEYS = {"authorization", "cookie", "token", "access_token", "api_key", "password", "secret", "secret_inputs", "runtime_inputs"}


def candidate_hash(candidate: dict) -> str:
    return hashlib.sha256(json.dumps(candidate, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def safe_context(value: Any):
    if isinstance(value, dict):
        if str(value.get("name", "")).lower() in SENSITIVE_KEYS:
            return {"name": value["name"], "data": {"masked": True}}
        return {k: safe_context(v) for k, v in value.items() if k.lower() not in SENSITIVE_KEYS and not k.lower().endswith("_token")}
    if isinstance(value, list):
        return [safe_context(v) for v in value[:100]]
    if isinstance(value, str):
        value = re.sub(r"(?:Bearer\s+\S+|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)", "[redacted]", value)
        return re.sub(r"(?i)((?:password|密码|api_key|secret|token)\s*[:=：]\s*)[^,\s;，；]+", r"\1[redacted]", value)
    return value


def validate_candidate(domain: str, candidate: dict, source: dict) -> dict:
    if len(json.dumps(candidate, ensure_ascii=False)) > 150_000:
        raise BusinessRuleError("候选内容超出限制")
    value = deepcopy(candidate)
    if not str(value.get("name") or "").strip():
        raise BusinessRuleError("请填写用例名称")
    value["case_type"] = domain
    value["source_id"] = source["id"]
    if not isinstance(value.get("input_info", {}), dict) or not isinstance(value.get("variables", {}), dict):
        raise BusinessRuleError("输入信息和变量必须是对象")
    value["variables"] = {**value.get("variables", {}), **value.get("input_info", {})}
    if not isinstance(value.get("assertions", []), list):
        raise BusinessRuleError("断言必须是数组")
    if domain == "API":
        data = source.get("data") or {}
        value["method"] = data.get("method")
        value["path"] = data.get("path")
        value.pop("url", None)
        value["auth_id"] = data.get("auth_id")
        for key in ("body", "query", "headers", "path_params", "input_info"):
            if key in value and not isinstance(value[key], dict):
                raise BusinessRuleError(f"{key} 必须是对象")
        if any(k.lower() in {"authorization", "cookie"} for k in (value.get("headers") or {})):
            raise BusinessRuleError("鉴权必须引用项目鉴权配置，不能在候选中保存 Token")
        supported = {"status", "status_in", "status_class", "status_not_5xx", "duration", "response_time", "body_contains", "message_contains", "content_type_in", "response_header", "json_equals"}
        if not value.get("assertions") or any(not isinstance(a, dict) or a.get("type") not in supported for a in value["assertions"]):
            raise BusinessRuleError("API 候选必须提供执行器支持的断言")
        return value
    if domain == "APP":
        from app.services.app_scenario_generation_service import SUPPORTED_ACTIONS
        actions = SUPPORTED_ACTIONS
    else:
        actions = WEB_ACTIONS
    steps = value.get("steps")
    if not isinstance(steps, list) or not 1 <= len(steps) <= 60:
        raise BusinessRuleError("操作步骤必须为 1 至 60 条")
    from app.services.web_input_policy_service import bind_input_steps, normalize_parameters
    parameters = normalize_parameters((source.get('data') or {}).get('parameters')) if domain == 'WEB' else []
    if domain == 'WEB':
        steps = value['steps'] = bind_input_steps(steps, parameters)
    manual_keys = {p['key'] for p in parameters if p['type'] in {'manual', 'password'}}
    for index, step in enumerate(steps, 1):
        if not isinstance(step, dict) or step.get("action") not in actions:
            raise BusinessRuleError(f"第 {index} 步动作不支持")
        step["sort_order"] = index
        step["take_screenshot"] = True
        step.pop("skip", None)
        if domain == 'APP' and step['action'] in {'tap','input','clear','select','assert','assert_text'}:
            if not step.get('locator') and not any(step.get(key) is not None for key in ('x','y','x_pct','y_pct')):
                raise BusinessRuleError(f'第 {index} 步需要定位或坐标')
        if domain == "WEB":
            if step["action"] == "wait":
                step["value"] = min(5000, max(0, int(step.get("value") or 500)))
                continue
            if step.get("locator_type") not in LOCATORS or not str(step.get("locator") or "").strip():
                raise BusinessRuleError(f"第 {index} 步需要有效的定位方式和定位内容")
            for key in ("selector", "css_selector", "playwright_locator", "data", "ai_cache"):
                step.pop(key, None)
            step["require_unique"] = True
            if step["action"] == "manual":
                match = re.fullmatch(r'\{\{([A-Za-z_][A-Za-z0-9_]*)\}\}', str(step.get('value') or ''))
                if match:
                    manual_keys.add(match[1])
                step.pop("value", None)
                step["take_screenshot"] = False
            if step.get('sensitive'):
                match = re.fullmatch(r'\{\{([A-Za-z_][A-Za-z0-9_]*)\}\}', str(step.get('value') or ''))
                if not match:
                    raise BusinessRuleError('密码步骤必须引用输入参数，不能保存明文密码')
                manual_keys.add(match[1])
                step['input_key'] = match[1]
                step['take_screenshot'] = False
            if step.get("frame_selector") is not None and (not isinstance(step["frame_selector"], str) or len(step["frame_selector"]) > 512):
                raise BusinessRuleError(f"第 {index} 步 iframe 定位无效")
            if step["action"] == "assert" and (step.get("expected") is None or str(step.get("expected")) == ""):
                raise BusinessRuleError(f"第 {index} 步断言需要 expected")
    if domain == "WEB":
        value["url"] = (source.get("data") or {}).get("url")
        for field in ('input_info', 'variables'):
            value[field] = {k: v for k, v in value.get(field, {}).items() if k not in manual_keys and not re.search(r'password|passwd|captcha|^otp$|verification.?code|验证码|密码', k, re.I)}
    if not isinstance(value.get("input_info", {}), dict):
        raise BusinessRuleError("输入信息必须是对象")
    if domain not in {"WEB", "APP"} and not any(s.get("action", "").startswith("assert") for s in steps) and not value.get("assertions"):
        raise BusinessRuleError("请至少添加一条结果断言")
    return value


def has_side_effects(candidate: dict) -> bool:
    # Even an innocuous-looking click can submit a form. Require explicit approval.
    return any(s.get("action") not in {"assert", "wait", "hover"} for s in candidate.get("steps", []))
