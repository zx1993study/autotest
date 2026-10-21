"""Collect the immutable historical responses used to rebuild old flow fixtures."""
import json
import os
import re

import case_suite_runner as core
from case_suite_runner import HERE, Platform, write_json


def sanitize(value, key=""):
    if re.search(r"password|hashed_password|authorization|access_token|refresh_token|cookie|secret", key, re.I):
        return "***"
    if isinstance(value, dict):
        return {name: sanitize(item, name) for name, item in value.items()}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    return value


def main():
    core.MANAGEMENT = "http://127.0.0.1:8000/api/v1"
    api = Platform()
    flows = json.loads((HERE / "native-flow-audit-local.json").read_text(encoding="utf-8"))["flows"]
    summary = json.loads((HERE / "case-coverage-final.json").read_text(encoding="utf-8"))
    scenes = {scene["code"]: scene for scene in summary["scenarios"]}
    needed = {}
    for flow in flows:
        code = flow["name"].removeprefix("CASEMD ")
        for evidence in scenes[code]["evidence"]:
            needed[evidence["record_id"]] = code
    output = HERE / "native-replay-old-records.json"
    records = sanitize(json.loads(output.read_text(encoding="utf-8"))) if output.exists() else {}
    for index, record_id in enumerate(needed):
        if str(record_id) not in records:
            records[str(record_id)] = sanitize(api.call("GET", f"/reports/records/{record_id}"))
        if index % 25 == 0:
            write_json(output, records)
            print("COLLECTED", index + 1, "/", len(needed), flush=True)
    write_json(output, records)
    bad = []
    for record_id, code in needed.items():
        body = records[str(record_id)]["data"].get("response_body", "")
        try:
            json.loads(body)
        except (ValueError, TypeError):
            bad.append({"record_id": record_id, "code": code, "length": len(body or "")})
    print(json.dumps({"records": len(needed), "truncated": bad}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
