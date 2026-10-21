import re


def inferred_case_field(name: str) -> str:
    match = re.match(r"^\[[^\]]+\]\s*([A-Za-z_][\w.\[\]-]*)(?=\s*(?:=|$))", name)
    return match[1] if match else ""


def case_report_metadata(case, request):
    data = case.get("data") or {}
    name = str(case.get("name") or "")
    field = data.get("field_name") or data.get("target_field")
    return {
        "api_path": str(request.get("path") or data.get("path") or data.get("api_path") or ""),
        "field_name": field if isinstance(field, str) else inferred_case_field(name),
        "test_point": str(data.get("test_point") or name),
    }
