"""Read-only inventory of native API-function scenarios and executions."""
import json
import argparse

import case_suite_runner
from case_suite_runner import HERE, PROJECT_ID, Platform, write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=case_suite_runner.MANAGEMENT)
    parser.add_argument("--output", default="native-flow-audit.json")
    args = parser.parse_args()
    assert args.base_url in {"https://dev-cn-01.yios.cn/autotest/api/v1", "http://127.0.0.1:8000/api/v1"}
    case_suite_runner.MANAGEMENT = args.base_url
    api = Platform()
    flows = []
    for page in range(1, 20):
        batch = api.call("GET", f"/execution/flows?project_id={PROJECT_ID}&pageSize=200&page={page}")
        flows.extend(batch["items"])
        if len(flows) >= batch["total"]:
            break
    result = {"project_id": PROJECT_ID, "flows": []}
    for flow in flows:
        row = {"id": flow["id"], "name": flow["name"], "status": flow["status"], "data": flow["data"]}
        for key in ("scenarios", "runs"):
            try:
                row[key] = api.call("GET", f"/execution/flows/{flow['id']}/{key}")
            except Exception as error:
                row[key + "_error"] = str(error)
        result["flows"].append(row)
    result["management_url"] = args.base_url
    write_json(HERE / args.output, result)
    print(json.dumps({"flows": len(flows), "scenario_count": sum(len(row.get("scenarios", [])) for row in result["flows"]),
        "run_count": sum(len(row.get("runs", [])) for row in result["flows"]),
        "first_flows": [{"id": row["id"], "name": row["name"], "status": row["status"],
            "scenario_count": len(row.get("scenarios", [])), "run_count": len(row.get("runs", [])),
            "error": row.get("scenarios_error")} for row in result["flows"][:8]]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
