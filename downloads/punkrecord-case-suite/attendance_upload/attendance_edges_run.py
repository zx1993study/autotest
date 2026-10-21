"""Run attendance boundaries and collect full duplicate-name evidence."""
import json

from bootstrap import HERE, save
from inspect_target import get, sessions
from run import accounts, execute_one, guarded_cleanup


def main():
    manager = sessions()["manager"]
    scenes = json.loads((HERE / "edges-applied.json").read_text(encoding="utf-8"))
    scenes.append({"id": 21145, "kind": "duplicate", "day": "2026-10-21"})
    report = {"runs": []}
    for scene in scenes:
        baseline = accounts(manager)
        assert get(manager, "/meeting/records", meeting_type="morning", search=scene["day"], limit=1)["total"] == 0
        row = execute_one(scene["id"])
        result = row["data"]["results"][0]
        item = {"scene": scene, "batch_id": row["id"], "status": row["status"], "result": result}
        report["runs"].append(item)
        save(HERE / "edges-execution.json", report)
        item["cleanup"] = guarded_cleanup(manager, result)
        item["balances_restored"] = accounts(manager) == baseline
        item["remaining_meetings"] = get(manager, "/meeting/records", meeting_type="morning", search=scene["day"], limit=1)["total"]
        save(HERE / "edges-execution.json", report)
        assert item["balances_restored"] and item["remaining_meetings"] == 0, "Stop on cleanup drift"
        failed = [{"key": n["key"], "assertions": [a for a in n.get("assertions", []) if not a.get("passed")]}
                  for n in result["nodes"] if n["status"] == "failed"]
        print(json.dumps({"scene_id": scene["id"], "batch_id": row["id"], "status": row["status"], "failed": failed}, ensure_ascii=True), flush=True)


if __name__ == "__main__":
    main()
