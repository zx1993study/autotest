"""Use supported dynamic generators and validate all inputs before replay."""
import json
from copy import deepcopy

from bootstrap import HERE, CampaignRepository, save
from inspect_target import sessions
from review_cleanup import account_state
from review_run import inputs
from web_automation.dynamic_values import DynamicValueContext

from app.db.session import SessionLocal
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.api_flow_scenario_service import ApiFlowScenarioService
from app.services.api_flow_run_service import ApiFlowRunService


def configure():
    scenes = json.loads((HERE / "review-applied.json").read_text(encoding="utf-8"))
    clients = sessions()
    accounts = account_state(clients["manager"])
    changed = []
    with SessionLocal() as db:
        repository = CampaignRepository(SqlAlchemyResourceRepository(db))
        rows, _ = repository.list("api_flow_runs", project_id=17796, page_size=10000)
        for row in rows:
            if row["status"] in {"queued", "running"}:
                ApiFlowRunService(repository).get_for_flow(row["data"]["flow_id"], row["id"])
        for index, scene in enumerate(scenes):
            row = repository.get("api_flow_scenarios", scene["scene_id"])
            data = deepcopy(row["data"])
            values = data["inputs"]
            for key, value in list(values.items()):
                if value == "{{uuid}}":
                    head, tail = key + "_head", key + "_tail"
                    values[head] = {"generator": "random_digits", "length": 8}
                    values[tail] = {"generator": "random_digits", "length": 12}
                    values[key] = "{{" + head + "}}-0000-4000-8000-{{" + tail + "}}"
            values.update(inputs(scene, accounts, index))
            for override in data["nodes"].values():
                request = override.get("request") or {}
                path = request.get("path", "")
                for configured in override.get("bindings") or []:
                    token = "{" + configured.get("path", "").removeprefix("/") + "}"
                    if configured["target"] == "params" and token in path:
                        path = path.replace(token, "{{bound_" + configured["name"] + "}}")
                        request.get("params", {}).pop(configured["path"].removeprefix("/"), None)
                        configured.update(target="variables", path="/" + configured["name"])
                if path:
                    request["path"] = path
            DynamicValueContext(values).resolve(values)
            ApiFlowScenarioService(repository).update_for_flow(scene["flow_id"], scene["scene_id"], {"data": data})
            changed.append(scene["scene_id"])
    save(HERE / "review-input-validation.json", {"validated_scenes": changed})
    print(json.dumps({"validated": len(changed)}))


if __name__ == "__main__":
    configure()
