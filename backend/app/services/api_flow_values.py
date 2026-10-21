import json
import re
from copy import deepcopy

from jsonpointer import JsonPointer, JsonPointerException, resolve_pointer, set_pointer

SENSITIVE_NAME = re.compile(r"password|passwd|secret|token|authorization|cookie|api[_-]?key", re.IGNORECASE)


def compare(actual, operator, expected):
    if operator == "exists":
        return actual is not None
    if operator == "eq":
        return type(actual) is type(expected) and actual == expected
    if operator == "ne":
        return not compare(actual, "eq", expected)
    try:
        return {"gt": lambda: actual > expected, "ge": lambda: actual >= expected,
                "lt": lambda: actual < expected, "le": lambda: actual <= expected,
                "contains": lambda: expected in actual}[operator]()
    except (TypeError, KeyError):
        return False


def response_value(response, spec):
    if spec.get("mode") == "array":
        return [response_value(response, {**spec, "mode": "single", "path": path}) for path in spec["paths"]]
    source = spec["source"]
    if source == "status":
        return response.get("status")
    if source == "header":
        name = spec.get("path", "")
        return next((v for k, v in response["headers"].items() if k.lower() == name.lower()), None)
    try:
        body = json.loads(response.get("body") or "null")
        selection = spec.get("selection")
        if selection:
            rows = resolve_pointer(body, selection["path"])
            if not isinstance(rows, list):
                return None
            body = next((row for row in rows if _selected_row(row, selection)), None)
        return resolve_pointer(body, spec.get("path", ""))
    except (ValueError, JsonPointerException, TypeError):
        return None


def _selected_row(row, selection):
    try:
        for path in selection.get("non_empty", []):
            value = resolve_pointer(row, path)
            if value in (None, "", [], {}) or (isinstance(value, str) and not value.strip()):
                return False
        return all(compare(resolve_pointer(row, path), "eq", value)
                   for path, value in selection.get("equals", {}).items())
    except (JsonPointerException, TypeError):
        return False


def variable_value(variables, reference):
    scope = variables.get(reference["source"], {})
    if reference["name"] not in scope:
        raise ValueError(f"缺少上游参数 {reference['source']}.{reference['name']}")
    return deepcopy(scope[reference["name"]])


def bind_value(request, binding, variables):
    value = variable_value(variables, binding)
    if binding.get("prefix"):
        value = binding["prefix"] + str(value)
    if binding["target"] == "auto":
        _bind_automatic(request, binding["target_name"], value)
        return
    target = request.setdefault(binding["target"], {})
    parts = JsonPointer(binding["path"]).parts
    if not parts:
        raise ValueError("参数目标路径不能为空")
    parent = target
    for part in parts[:-1]:
        if isinstance(parent, dict):
            parent = parent.setdefault(part, {})
        elif isinstance(parent, list):
            parent = parent[int(part)]
        else:
            raise TypeError("参数目标路径与请求数据类型不匹配")
    set_pointer(target, binding["path"], value, inplace=True)


def _matching_fields(container, name, path):
    matches = []
    if isinstance(container, dict):
        for key, value in container.items():
            field_path = f"{path}/{str(key).replace('~', '~0').replace('/', '~1')}"
            if key == name:
                matches.append((container, key, field_path))
            matches.extend(_matching_fields(value, name, field_path))
    elif isinstance(container, list):
        for index, value in enumerate(container):
            matches.extend(_matching_fields(value, name, f"{path}/{index}"))
    return matches


def _bind_automatic(request, name, value):
    params = request.setdefault("params", {})
    if isinstance(params, dict) and name in params:
        params[name] = value
        return
    matches = []
    for section in ("params", "body", "query", "headers"):
        matches.extend(_matching_fields(request.get(section), name, f"/{section}"))
    if len(matches) > 1:
        paths = "、".join(match[2] for match in matches)
        raise ValueError(f"目的变量 {name} 存在多个同名字段：{paths}，请使用不重复的参数名")
    if matches:
        parent, key, _ = matches[0]
        parent[key] = value
    elif isinstance(params, dict):
        params[name] = value
    else:
        raise TypeError("API 参数必须为对象，无法自动关联参数")


def apply_request_override(request, configured):
    for key, value in configured.get("request", {}).items():
        inherited = request.get(key)
        if key in {"headers", "params", "query"} and isinstance(value, dict):
            request[key] = {**(inherited if isinstance(inherited, dict) else {}), **deepcopy(value)}
        else:
            request[key] = deepcopy(value)
    inherited = request.get("params")
    request["params"] = {**(inherited if isinstance(inherited, dict) else {}), **deepcopy(configured.get("params", {}))}
    for path in configured.get("request_removals", []):
        parts = JsonPointer(path).parts
        parent = request if len(parts) == 1 else request.get(parts[0])
        if isinstance(parent, dict):
            parent.pop(parts[-1], None)


class EvidenceMask:
    def __init__(self, inputs):
        self.secrets = set()
        self.collect(inputs)

    def collect(self, value, name=""):
        if SENSITIVE_NAME.search(name):
            self.add(value)
        if isinstance(value, dict):
            for key, item in value.items():
                self.collect(item, str(key))
        elif isinstance(value, list):
            for item in value:
                self.collect(item)

    def add(self, value):
        if isinstance(value, (list, dict)):
            for item in value.values() if isinstance(value, dict) else value:
                self.add(item)
            return
        if isinstance(value, str) and value:
            self.secrets.add(value)
            if value.startswith("Bearer "):
                self.secrets.add(value[7:])

    def clean(self, value, name=""):
        if SENSITIVE_NAME.search(name):
            return "***"
        if isinstance(value, dict):
            return {key: self.clean(item, str(key)) for key, item in value.items()}
        if isinstance(value, list):
            return [self.clean(item) for item in value]
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, (dict, list)):
                    return json.dumps(self.clean(parsed), ensure_ascii=False)
            except ValueError:
                pass
            for secret in sorted(self.secrets, key=len, reverse=True):
                value = value.replace(secret, "***")
        return value
