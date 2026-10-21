"""One shared meeting-upload template with complete business branches."""
from copy import deepcopy

PROJECT_ID = 17796
FLOW_ID = 21138
EMPLOYEE = "0830f805-3a2f-4ce2-a6d4-b0055a3b88f5"
DUPLICATE_EMPLOYEE = "640d1a5c-bff5-4df0-9e02-cb42f8b46413"
OK = [{"type": "status", "expected": 200}, {"type": "json_pointer", "path": "/code", "expected": 0}]
ROUTES = {
    "meetings": ("GET", "/meeting/records", 20373),
    "create": ("POST", "/meeting/records", 20373),
    "upload": ("POST", "/meeting/records/{meeting_id}/upload-transcript", 20373),
    "detail": ("GET", "/meeting/records/{meeting_id}", 20373),
    "delete": ("DELETE", "/meeting/records/{meeting_id}", 20373),
    "attendance": ("GET", "/beli/attendance", 20374),
    "accounts": ("GET", "/beli/accounts", 20374),
    "ledger": ("GET", "/beli/ledger", 20374),
    "attendance_admin": ("GET", "/beli/attendance", 20373),
    "duplicate_attendance": ("GET", "/beli/attendance", 20375),
    "duplicate_accounts": ("GET", "/beli/accounts", 20375),
    "duplicate_ledger": ("GET", "/beli/ledger", 20375),
}
STEPS = [
    ("date_guard", "attendance", "校验会议日期与已有考勤状态"),
    ("guard", "meetings", "核对测试日期没有既有早会"),
    ("baseline", "accounts", "记录测试员工余额"),
    ("ledger_before", "ledger", "记录测试员工流水"),
    ("create", "create", "创建本场景会议"),
    ("upload", "upload", "上传 Word 文稿"),
    ("detail", "detail", "核对文稿解析与参会人"),
    ("attendance", "attendance", "核对早会出缺席与扣款状态"),
    ("ambiguous_name", "attendance_admin", "核对同名讲话人进入未匹配名单"),
    ("balance", "accounts", "核对贝利余额变化"),
    ("ledger", "ledger", "核对贝利流水"),
    ("upload_again", "upload", "重复上传或更正文稿"),
    ("detail_again", "detail", "核对更新后的参会人"),
    ("attendance_again", "attendance", "核对重复处理或更正后的考勤"),
    ("balance_again", "accounts", "核对不重复扣款或退还贝利"),
    ("ledger_again", "ledger", "核对防重或冲正流水"),
    ("cleanup", "delete", "删除仅本次创建的会议"),
    ("balance_restored", "accounts", "核对清理后恢复原余额"),
]


def equal(path, expected):
    return {"type": "json_pointer", "path": path, "expected": expected}


def extract(name, path):
    return {"name": name, "source": "body", "path": path, "required": True}


def binding(source, name, target="variables", path=None):
    return {"source": source, "name": name, "target": target, "path": path or "/" + name}


def rows(path, rules, minimum=1, maximum=1):
    return {"type": "json_query_result", "path": path, "min_items": minimum,
            "max_items": maximum, "rules": [{"paths": [key], "operator": "eq", "expected": value}
                                            for key, value in rules.items()]}


def definition(resources):
    return {"inputs": {"attendance_day": "CONFIGURE_TEST_WORKDAY"}, "nodes": [
        {"key": key, "name": name, "api_id": resources[route]["api_id"],
         "case_id": resources[route]["case_id"]} for key, route, name in STEPS
    ]}


def initial_nodes(kind, resources):
    duplicate = kind == "duplicate"
    nodes = {}
    for key, route, _ in STEPS:
        method, path, _ = ROUTES[route]
        nodes[key] = {"request": {"method": method, "path": path, "body": {}, "query": {}},
                      "assertions": deepcopy(OK), "bindings": [], "extracts": []}
        if duplicate and route in {"accounts", "attendance", "ledger"} and resources:
            nodes[key]["case_id"] = resources["duplicate_" + route]["case_id"]
        if "{meeting_id}" in path:
            nodes[key]["bindings"] = [binding("create", "meeting_id")]
            nodes[key]["request"]["path"] = path.replace("{meeting_id}", "{{bound_meeting_id}}")
    nodes["date_guard"]["request"]["query"] = {"day": "{{attendance_day}}"}
    nodes["date_guard"]["assertions"] += [rows("/data/items", {"/charged": False, "/waived": False}, minimum=0)]
    nodes["guard"]["request"]["query"] = {"meeting_type": "morning", "search": "{{attendance_day}}", "limit": 1}
    nodes["guard"]["assertions"] += [equal("/data/total", 0)]
    return nodes


def scenario(kind, files, names, day="CONFIGURE_TEST_WORKDAY", resources=None):
    weekly, present = kind == "weekly", kind == "present"
    repeated, corrected = kind == "repeat", kind == "correction"
    duplicate = kind == "duplicate"
    employee = DUPLICATE_EMPLOYEE if duplicate else EMPLOYEE
    first = "provided" if duplicate else "present" if present or weekly else "absent"
    nodes = initial_nodes(kind, resources)
    nodes["baseline"]["assertions"] += [rows("/data/items", {"/user_id": employee})]
    nodes["baseline"]["extracts"] = [extract("balance", "/data/items/0/balance")]
    for key in ("ledger_before", "ledger", "ledger_again"):
        nodes[key]["request"]["query"] = {"user_id": employee, "page": 1}
        nodes[key]["extracts"] = [extract("entries", "/data")]
    nodes["create"]["request"].update(content_type="application/x-www-form-urlencoded", body={
        "title": "早会文稿链路-" + kind + "-{{timestamp_ms}}", "meeting_date": "{{attendance_day}}",
        "meeting_type": "weekly" if weekly else "morning",
    })
    nodes["create"]["extracts"] = [extract("meeting_id", "/data/id")]
    for suffix, variant in (("", first), ("_again", "present" if corrected else first)):
        import_checks(nodes, suffix, variant, {"kind": kind, "employee": employee, "files": files, "names": names})
    nodes["ambiguous_name"]["request"]["query"] = {"day": "{{attendance_day}}"}
    nodes["ambiguous_name"]["assertions"] += [{"type": "json_query_result", "path": "/data", "collection": False,
        "rules": [{"paths": ["/unmatched_names"], "operator": "tokens", "expected": ["test_user3"]}]}]
    if not duplicate:
        nodes["ambiguous_name"]["mode"] = "skip"
    if kind == "invalid":
        nodes["upload"]["request"]["files"] = [files["invalid"]]
        nodes["upload"]["assertions"] = [{"type": "api_rejection", "expected": "validation"}]
        nodes["detail"]["assertions"] = deepcopy(OK) + [equal("/data/status", "transcribed"), equal("/data/attendees", None)]
    if not (repeated or corrected):
        for key in nodes:
            if key.endswith("_again"):
                nodes[key]["mode"] = "skip"
                nodes[key]["bindings"] = []
    nodes["balance_restored"]["bindings"] = [binding("baseline", "balance")]
    nodes["balance_restored"]["assertions"] += [
        {"type": "json_number_delta", "path": "/data/items/0/balance", "baseline": "{{bound_balance}}", "expected": 0}]
    label = {"present": "文稿出席不扣款", "absent": "文稿缺席扣除500贝利", "repeat": "重复上传不重复扣款",
             "correction": "补传出席文稿退还已扣贝利", "weekly": "周会上传不产生早会扣款",
             "duplicate": "文稿同名人员未映射不自动认定出席", "invalid": "无效文稿拒绝后会议可查且不重复扣款"}[kind]
    return {"name": "ATT-UPLOAD-" + kind.upper() + " " + label, "status": "active",
            "description": "选择文稿→创建会议→上传文稿→核对参会人/考勤/余额/流水→仅清理本次会议；串行执行",
            "data": {"inputs": {"attendance_day": day}, "nodes": nodes,
                     "failure_policy": "stop", "expected_end": "balance_restored"}}


def import_checks(nodes, suffix, variant, context):
        files, names, employee = context["files"], context["names"], context["employee"]
        weekly, repeated, duplicate = (context["kind"] == key for key in ("weekly", "repeat", "duplicate"))
        nodes["upload" + suffix]["request"].update(content_type="multipart/form-data", files=[files[variant]])
        nodes["upload" + suffix]["assertions"] += [equal("/data/meeting/status", "transcribed")]
        nodes["detail" + suffix]["assertions"] += [equal("/data/attendees", names[variant]),
            equal("/data/meeting_type", "weekly" if weekly else "morning"), equal("/data/status", "transcribed")]
        attend = nodes["attendance" + suffix]
        attend["request"]["query"] = {"day": "{{attendance_day}}"}
        charged = (variant == "absent" or duplicate) and not weekly
        attend["assertions"] += [rows("/data/items", {"/user_id": employee,
            "/day": "{{attendance_day}}", "/absent": charged, "/charged": charged, "/waived": False},
            minimum=0 if weekly else 1, maximum=1)]
        balance = nodes["balance" + suffix]
        balance["bindings"] = [binding("baseline", "balance")]
        balance["assertions"] += [rows("/data/items", {"/user_id": employee}),
            {"type": "json_number_delta", "path": "/data/items/0/balance",
             "baseline": "{{bound_balance}}", "expected": -500 if charged else 0}]
        ledger = nodes["ledger" + suffix]
        if weekly or repeated and suffix:
            ledger["bindings"] = [binding("ledger" if suffix else "ledger_before", "entries")]
            ledger["assertions"] += [equal("/data", "{{bound_entries}}")]
        else:
            ledger["assertions"] += [equal("/data/0/user_id", employee),
                equal("/data/0/details/day", "{{attendance_day}}"),
                equal("/data/0/kind", "attendance" if charged else "attendance_reverse"),
                {"type": "json_number_delta", "path": "/data/0/amount", "baseline": 0,
                 "expected": -500 if charged else 500}]
