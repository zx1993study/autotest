"""Load batch references once before validating and freezing each scenario."""

from app.repositories.api_flow_snapshot_repository import ApiFlowSnapshotRepository
from app.services.api_flow_snapshot_service import ApiFlowSnapshotService
from app.services.api_flow_validation import validate_references


class ApiFlowPreparationService:
    def __init__(self, repository):
        self.repository = repository

    def build(self, flow, scenarios, inputs):
        repository = ApiFlowSnapshotRepository(self._load_references(flow, scenarios))
        service = ApiFlowSnapshotService(repository)
        snapshots = []
        for scenario in scenarios:
            validate_references(repository, flow["project_id"], flow["data"], scenario["data"], running=True)
            snapshots.append(service.build(flow, scenario, inputs))
        return snapshots

    def _load_references(self, flow, scenarios):
        nodes = flow["data"]["nodes"]
        case_ids = {
            scenario["data"]["nodes"].get(node["key"], {}).get("case_id") or node.get("case_id")
            for scenario in scenarios for node in nodes
        } - {None}
        tables = {
            "projects": self.repository.get_many("projects", [flow["project_id"]]),
            "api_interfaces": self.repository.get_many("api_interfaces", list({node["api_id"] for node in nodes})),
            "api_test_cases": self.repository.get_many("api_test_cases", list(case_ids)),
        }
        auth_ids = {node.get("auth_id") for node in nodes}
        for item in [*tables["api_interfaces"], *tables["api_test_cases"]]:
            data = item.get("data") or {}
            legacy = data.get("request") if isinstance(data.get("request"), dict) else {}
            auth_ids.add(data.get("auth_id") or legacy.get("auth_id"))
        tables["project_auth"] = self.repository.get_many("project_auth", list(auth_ids - {None}))
        strategies = {key for case in tables["api_test_cases"] for key in (case.get("strategy_ids") or [])}
        tables["project_knowledge"] = self.repository.get_many("project_knowledge", list(strategies))
        for table, limit in (("api_fields", 10000), ("api_import_tasks", 20)):
            tables[table], _ = self.repository.list(table, project_id=flow["project_id"], page_size=limit)
        return tables
