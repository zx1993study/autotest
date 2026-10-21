"""Run the saved business scenes serially; preserve every failure and cleanup."""
import json
import re
import sys
from datetime import date, timedelta
from decimal import Decimal

from bootstrap import HERE, save
from inspect_target import sessions
from review_cleanup import account_state, cleanup
from review_common import EMPLOYEE
from run import execute_one


def inputs(scene, accounts, index):
    late = re.search(r"BELI02-p\d-(\d+)", scene["name"])
    due = date(2026, 10, 21) - timedelta(days=int(late[1]) if late else 0)
    leave_day = date(2027, 2, 1) + timedelta(days=index * 7)
    available = Decimal(str(accounts[EMPLOYEE]["available"]))
    balance = Decimal(str(accounts[EMPLOYEE]["balance"]))
    return {"task_due_at": due.isoformat() + "T18:00:00+08:00",
            "leave_start": leave_day.isoformat() + "T09:00:00+08:00",
            "leave_end": leave_day.isoformat() + "T12:00:00+08:00",
            "exact_price": str(available), "negative_exact_price": str(-available),
            "decrease_amount": str(Decimal(80) - balance), "restore_amount": str(balance - Decimal(80))}


def main():
    scenes = json.loads((HERE / "review-applied.json").read_text(encoding="utf-8"))
    clients = sessions()
    manager = clients["manager"]
    path = HERE / "review-execution.json"
    resume = any(flag in sys.argv for flag in ("--resume", "--retry-failed", "--verify-rejections"))
    report = json.loads(path.read_text(encoding="utf-8")) if resume and path.exists() else {"runs": []}
    latest = {item["scene"]["scene_id"]: item for item in report["runs"]}
    done = {scene_id for scene_id, item in latest.items()
            if item["status"] == "success"} if "--retry-failed" in sys.argv else {
                scene_id for scene_id, item in latest.items() if item["result"].get("nodes")}
    selected = set(json.loads((HERE / "rejections-applied.json").read_text(encoding="utf-8"))) if "--verify-rejections" in sys.argv else None
    for index, scene in enumerate(scenes):
        if selected is not None and scene["scene_id"] not in selected:
            continue
        if selected is None and scene["scene_id"] in done:
            continue
        before = account_state(manager)
        values = inputs(scene, before, index)
        row = execute_one(scene["scene_id"], scene["flow_id"], values)
        result = row["data"]["results"][0]
        item = {"scene": scene, "batch_id": row["id"], "status": row["status"], "inputs": values, "result": result}
        report["runs"].append(item)
        save(path, report)
        if not result.get("nodes"):
            raise RuntimeError("Executor failed before sending requests; stop and repair configuration")
        try:
            item["cleanup"] = cleanup(manager, result, before)
            item["cleanup_success"] = True
        except Exception as exc:
            item.update(cleanup_success=False, cleanup_error=str(exc))
            save(path, report)
            raise
        save(path, report)
        failed = [{"key": n["key"], "error": n.get("error"), "http": n.get("response_status"),
                   "assertions": [a for a in n.get("assertions", []) if not a.get("passed")]}
                  for n in result["nodes"] if n["status"] == "failed"]
        print(json.dumps({"scene_id": scene["scene_id"], "group": scene["group"], "batch_id": row["id"],
                          "status": row["status"], "failed": failed}, ensure_ascii=True), flush=True)
    report["summary"] = {status: sum(item["status"] == status for item in report["runs"]) for status in ("success", "failed")}
    save(path, report)


if __name__ == "__main__":
    main()
