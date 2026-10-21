"""Add no-charge date boundaries using the existing shared upload template."""
import json
from copy import deepcopy

from bootstrap import HERE, CampaignRepository, save
from inspect_target import get, sessions
from plan import FLOW_ID, equal

from app.db.session import SessionLocal
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.api_flow_scenario_service import ApiFlowScenarioService


def main():
    assert not (HERE / "edges-applied.json").exists(), "Already added"
    manager = sessions()["manager"]
    calendar = get(manager, "/beli/calendar")
    assert not any(row["day"] == "2026-10-17" and row["is_workday"] for row in calendar)
    result = []
    with SessionLocal() as db:
        repository = CampaignRepository(SqlAlchemyResourceRepository(db))
        service = ApiFlowScenarioService(repository)
        source = service.get_for_flow(FLOW_ID, 21144)
        for kind, day, label in (("future", "2026-10-22", "未来早会上传不提前扣款"),
                                  ("weekend", "2026-10-17", "非工作日早会上传不扣款")):
            assert get(manager, "/meeting/records", meeting_type="morning", search=day, limit=1)["total"] == 0
            data = deepcopy(source["data"])
            data["inputs"]["attendance_day"] = day
            nodes = data["nodes"]
            nodes["create"]["request"]["body"].update(meeting_type="morning", title="早会文稿链路-" + kind + "-{{timestamp_ms}}")
            for key in ("detail", "detail_again"):
                for rule in nodes[key]["assertions"]:
                    if rule.get("path") == "/data/meeting_type":
                        rule["expected"] = "morning"
            data.pop("latest_status", None)
            data.pop("latest_run_id", None)
            row = service.create_for_flow(FLOW_ID, {"name": "ATT-UPLOAD-" + kind.upper() + " " + label,
                "status": "active", "description": "创建新会议→上传文稿→核对日期边界不结算→核对余额与流水不变→删除本次会议", "data": data})
            result.append({"id": row["id"], "kind": kind, "name": row["name"], "day": day})
        duplicate = service.get_for_flow(FLOW_ID, 21145)
        data = deepcopy(duplicate["data"])
        data["failure_policy"] = "continue"
        data["nodes"]["detail"]["assertions"].append(equal("/data/speaker_user_mapping", {}))
        service.update_for_flow(FLOW_ID, 21145, {"data": data})
    save(HERE / "edges-applied.json", result)
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
