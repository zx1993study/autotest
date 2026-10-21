import argparse
import asyncio
import json
import os
from pathlib import Path

from pages.list_page import execute

ROOT = Path(__file__).resolve().parent


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only source-generated Web scripts; no AI or business writes")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--case", type=int)
    target.add_argument("--feature", type=int)
    parser.add_argument("--base-url", default="https://test.waiqin.yios.cn")
    parser.add_argument("--storage-state", default=os.getenv("FIELDWORK_WEB_STORAGE_STATE"))
    parser.add_argument("--browser-executable", default=os.getenv("FIELDWORK_WEB_BROWSER"))
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--inputs", default=str(ROOT / "inputs.json"))
    parser.add_argument("--report", default=str(ROOT / "results/latest.json"))
    args = parser.parse_args(argv)
    catalog = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
    case = next((item for item in catalog["cases"] if item["case_id"] == args.case), None) if args.case else None
    if args.case and not case:
        parser.error("Unknown existing case ID")
    feature_id = case["feature_id"] if case else args.feature
    feature = next((item for item in catalog["features"] if item["feature_id"] == feature_id), None)
    if not feature:
        parser.error("Unknown existing feature ID")
    config = {**vars(args), "runtime_token": os.getenv("FIELDWORK_WEB_TOKEN")}
    reason = (case or feature).get("reason")
    blocked = (case or feature)["status"] != "source_ready"
    if not blocked and not args.storage_state and not config["runtime_token"]:
        blocked, reason = True, "Missing browser login state"
    if blocked:
        result = {"status": "blocked", "executed": False, "reason": reason,
                  "case_id": args.case, "feature_id": feature_id}
    else:
        inputs = json.loads(Path(args.inputs).read_text(encoding="utf-8-sig"))
        try:
            result = asyncio.run(execute(config, feature, case, inputs.get(str(args.case), {})))
            result["executed"] = True
        except Exception as exc:  # noqa: BLE001 - persist a sanitized failure, never credentials.
            result = {"status": "failed", "executed": True, "error_type": type(exc).__name__,
                      "case_id": args.case, "feature_id": feature_id,
                      "reason": "Browser replay failed; inspect locally without exporting credentials or customer payloads"}
    output = Path(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True))
    return result


if __name__ == "__main__":
    result = main()
    raise SystemExit(0 if result["status"] == "passed" else 2 if result["status"] == "blocked" else 1)
