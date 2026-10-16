"""Generate executable plan cases from configured project knowledge and assets."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from app.core.exceptions import BusinessRuleError, ResourceNotFoundError
from app.models.execution_plan import ExecutionPlan
from app.repositories.interfaces import ExecutionPlanRepository, ResourceRepository
from app.schemas.execution import (
    ExecutionPlanFeatureAddRequest,
    ExecutionPlanGenerationOut,
)
from app.services.execution_plan_service import ExecutionPlanService
from app.services.test_case_service import TestCaseService
from app.services.test_generation_service import GeneratedCaseSpec, TestGenerationService


MAX_GENERATED_PLAN_CASES = 500
GENERATED_PLAN_ID_KEY = "generated_plan_id"
GENERATED_PLAN_CASE_KEY = "generated_plan_case_key"


class ExecutionPlanGenerationService:
    """Build and synchronize executable formal cases for one plan."""

    def __init__(
        self,
        plan_repository: ExecutionPlanRepository,
        resource_repository: ResourceRepository,
    ) -> None:
        self.plan_repository = plan_repository
        self.resource_repository = resource_repository
        self.plan_service = ExecutionPlanService(plan_repository)
        self.case_generator = TestGenerationService(resource_repository)

    def generate(self, plan_id: int) -> ExecutionPlanGenerationOut:
        """Regenerate API/Web cases without duplicating prior generated rows."""

        plan = self._get_plan(plan_id)
        project_id = self._project_id(plan)
        api_ids = self._int_list(plan.api_ids_json)
        web_feature_ids = self._int_list(plan.web_feature_ids_json)
        if not api_ids and not web_feature_ids:
            raise BusinessRuleError("请先编辑执行计划并选择 API 或 Web 功能")

        knowledge_ids = self._knowledge_ids(project_id)
        specs = self._build_specs(
            project_id,
            api_ids,
            web_feature_ids,
            knowledge_ids,
        )
        if not specs:
            raise BusinessRuleError("未根据当前 API 或 Web 功能生成测试用例")
        if len(specs) > MAX_GENERATED_PLAN_CASES:
            raise BusinessRuleError("生成用例超过 500 条，请缩小 API 或 Web 功能范围")

        self._sync_formal_cases(plan, specs)
        self._sync_plan_snapshots(plan, api_ids, web_feature_ids)
        api_count = sum(1 for item in specs if item.case_type == "API")
        web_count = sum(1 for item in specs if item.case_type == "WEB")
        self.plan_service.record_generation(
            plan.id,
            self._generation_metadata(knowledge_ids, api_count, web_count),
        )
        detail = self.plan_service.detail(plan.id)
        return ExecutionPlanGenerationOut(
            plan_id=plan.id,
            knowledge_count=len(knowledge_ids),
            api_case_count=api_count,
            web_case_count=web_count,
            generated_case_count=len(specs),
            detail=detail,
        )

    def _build_specs(
        self,
        project_id: int,
        api_ids: list[int],
        web_feature_ids: list[int],
        knowledge_ids: list[int],
    ) -> list[GeneratedCaseSpec]:
        api_specs = (
            self.case_generator.build_api_case_specs(
                project_id,
                api_ids,
                "full",
                knowledge_ids,
            )
            if api_ids
            else []
        )
        web_specs = (
            self.case_generator.build_asset_case_specs(
                "WEB",
                "web_pages",
                "web_elements",
                project_id,
                web_feature_ids,
                "full",
                knowledge_ids,
            )
            if web_feature_ids
            else []
        )
        return [*api_specs, *web_specs]

    def _sync_formal_cases(
        self,
        plan: ExecutionPlan,
        specs: list[GeneratedCaseSpec],
    ) -> None:
        for case_type in ("API", "WEB"):
            domain_specs = [item for item in specs if item.case_type == case_type]
            self._sync_case_domain(plan, case_type, domain_specs)

    def _sync_case_domain(
        self,
        plan: ExecutionPlan,
        case_type: str,
        specs: list[GeneratedCaseSpec],
    ) -> None:
        service = TestCaseService(case_type, self.resource_repository)
        existing = service.list_generated_for_plan(self._project_id(plan), plan.id)
        existing_by_key = {
            str(self._dict_value(item.get("data")).get(GENERATED_PLAN_CASE_KEY)): item
            for item in existing
        }
        retained_ids: set[int] = set()
        source_indexes: dict[int, int] = defaultdict(int)
        for spec in specs:
            source_indexes[spec.source_id] += 1
            key = self._case_key(spec, source_indexes[spec.source_id])
            payload = self._formal_case_payload(plan, spec, key)
            current = existing_by_key.get(key)
            saved = (
                service.update(int(current["id"]), payload)
                if current is not None
                else service.create(payload)
            )
            retained_ids.add(int(saved["id"]))
        for item in existing:
            item_id = int(item["id"])
            if item_id not in retained_ids:
                service.delete(item_id)

    def _sync_plan_snapshots(
        self,
        plan: ExecutionPlan,
        api_ids: list[int],
        web_feature_ids: list[int],
    ) -> None:
        self.plan_repository.delete_generated_plan_cases(plan.id)
        selections = {"API": api_ids, "WEB": web_feature_ids}
        for case_type, feature_ids in selections.items():
            self.plan_repository.replace_plan_feature_selection(
                plan.id,
                case_type,
                set(feature_ids),
            )
            if feature_ids:
                self.plan_service.add_features(
                    plan.id,
                    ExecutionPlanFeatureAddRequest(
                        case_type=case_type,
                        feature_ids=feature_ids,
                    ),
                )

    def _knowledge_ids(self, project_id: int) -> list[int]:
        rows, _ = self.resource_repository.list(
            "project_knowledge",
            project_id=project_id,
            page=1,
            page_size=10000,
        )
        result: list[int] = []
        for item in rows:
            data = self._dict_value(item.get("data"))
            if item.get("status") != "active" or data.get("kind") != "test_principle":
                continue
            item_id = item.get("id")
            if isinstance(item_id, int):
                result.append(item_id)
        if not result:
            raise BusinessRuleError("当前项目没有启用的测试原则，请先初始化用例知识库")
        return result

    def _formal_case_payload(
        self,
        plan: ExecutionPlan,
        spec: GeneratedCaseSpec,
        key: str,
    ) -> dict[str, object]:
        case_json = dict(spec.case_json)
        case_json[GENERATED_PLAN_ID_KEY] = plan.id
        case_json[GENERATED_PLAN_CASE_KEY] = key
        return {
            "name": str(case_json.get("name") or "生成用例")[:128],
            "project_id": self._project_id(plan),
            "source_id": spec.source_id,
            "description": f"由执行计划《{plan.name}》自动生成",
            "status": "active",
            "data": case_json,
            "steps": self._dict_list(case_json.get("steps")),
            "assertions": self._dict_list(case_json.get("assertions")),
            "strategy_ids": self._int_list(case_json.get("strategy_ids")),
        }

    def _generation_metadata(
        self,
        knowledge_ids: list[int],
        api_count: int,
        web_count: int,
    ) -> dict[str, object]:
        return {
            "source": "configured_sources",
            "knowledge_ids": knowledge_ids,
            "api_case_count": api_count,
            "web_case_count": web_count,
            "generated_case_count": api_count + web_count,
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }

    def _get_plan(self, plan_id: int) -> ExecutionPlan:
        plan = self.plan_repository.get(plan_id)
        if plan is None:
            raise ResourceNotFoundError("执行计划不存在")
        return plan

    def _project_id(self, plan: ExecutionPlan) -> int:
        if plan.project_id is None:
            raise BusinessRuleError("执行计划未关联项目，无法生成测试用例")
        return plan.project_id

    def _case_key(self, spec: GeneratedCaseSpec, source_index: int) -> str:
        category = str(spec.case_json.get("category") or "case")
        return f"{spec.case_type}:{spec.source_id}:{source_index}:{category}"

    def _dict_value(self, value: object) -> dict[str, object]:
        return value if isinstance(value, dict) else {}

    def _dict_list(self, value: object) -> list[dict[str, object]]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]

    def _int_list(self, value: object) -> list[int]:
        if not isinstance(value, list):
            return []
        result: list[int] = []
        for item in value:
            try:
                parsed = int(item)
            except (TypeError, ValueError):
                continue
            if parsed > 0 and parsed not in result:
                result.append(parsed)
        return result
