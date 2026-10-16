"""Generate execution plans from page requirements and knowledge principles."""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.exceptions import BusinessRuleError
from app.enums.business import ExecutionPlanStatusEnum, ExecutionPlanTestTypeEnum
from app.models.execution_plan import ExecutionPlan
from app.repositories.interfaces import ExecutionPlanRepository, ResourceRepository
from app.schemas.knowledge import (
    KnowledgePlanGenerationOut,
    KnowledgePlanGenerationRequest,
)
from app.services.requirement_document_parser import RequirementDocumentParser


class KnowledgePlanGenerationService:
    """Coordinate knowledge reads and execution-plan persistence."""

    def __init__(
        self,
        knowledge_repository: ResourceRepository,
        plan_repository: ExecutionPlanRepository,
        requirement_parser: RequirementDocumentParser | None = None,
    ) -> None:
        self.knowledge_repository = knowledge_repository
        self.plan_repository = plan_repository
        self.requirement_parser = requirement_parser or RequirementDocumentParser()

    def generate(
        self,
        payload: KnowledgePlanGenerationRequest,
    ) -> KnowledgePlanGenerationOut:
        """Persist one plan and manual test snapshots derived from principles."""

        principles = self._load_principles(payload)
        requirement_items = self.requirement_parser.parse(
            payload.requirement_document
        )
        case_rows = self._generated_case_rows(
            principles,
            requirement_items,
            payload,
        )
        plan = self._create_plan(
            payload,
            principles,
            len(requirement_items),
            len(case_rows),
        )
        try:
            self._persist_case_rows(plan.id, case_rows)
        except Exception:  # noqa: BLE001 - compensate a partially persisted plan.
            self.plan_repository.delete(plan.id)
            raise
        return KnowledgePlanGenerationOut(
            plan_id=plan.id,
            generated_case_count=len(case_rows),
        )

    def _load_principles(
        self,
        payload: KnowledgePlanGenerationRequest,
    ) -> list[dict[str, object]]:
        principles: list[dict[str, object]] = []
        for principle_id in payload.principle_ids:
            item = self.knowledge_repository.get(
                "project_knowledge",
                principle_id,
            )
            if item is None:
                raise BusinessRuleError(f"测试原则 #{principle_id} 不存在")
            self._validate_principle(item, payload.project_id)
            principles.append(item)
        return principles

    def _validate_principle(
        self,
        item: dict[str, object],
        project_id: int,
    ) -> None:
        if item.get("project_id") not in (None, project_id):
            raise BusinessRuleError("不能使用其它项目的测试原则")
        if item.get("status") != "active":
            raise BusinessRuleError("停用的测试原则不能生成执行计划")
        data = self._object_value(item.get("data"))
        if data.get("kind") != "test_principle":
            raise BusinessRuleError("所选知识不是测试原则")

    def _generated_case_rows(
        self,
        principles: list[dict[str, object]],
        requirement_items: list[str],
        payload: KnowledgePlanGenerationRequest,
    ) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for principle in principles:
            scenarios = self._principle_scenarios(principle)
            for requirement_item in requirement_items:
                for scenario in scenarios:
                    rows.append(
                        self._case_row(
                            principle,
                            scenario,
                            payload.requirement_title,
                            requirement_item,
                            len(rows) + 1,
                        )
                    )
        if not rows:
            raise BusinessRuleError("所选测试原则没有可生成的测试场景")
        return rows

    def _principle_scenarios(
        self,
        principle: dict[str, object],
    ) -> list[dict[str, object]]:
        data = self._object_value(principle.get("data"))
        template = self._object_value(data.get("template_json"))
        scenarios = template.get("scenarios")
        if not isinstance(scenarios, list):
            return []
        return [self._object_value(item) for item in scenarios if isinstance(item, dict)]

    def _case_row(
        self,
        principle: dict[str, object],
        scenario: dict[str, object],
        requirement_title: str,
        requirement_item: str,
        sort_order: int,
    ) -> dict[str, object]:
        principle_id = int(principle["id"])
        principle_name = str(principle.get("name") or "测试原则")
        data = self._object_value(principle.get("data"))
        scenario_title = str(scenario.get("title") or "需求验证")
        case_name = f"{self._short_text(requirement_item, 72)} - {scenario_title}"
        return {
            "case_type": "MANUAL",
            "feature_id": principle_id,
            "feature_name": principle_name,
            "case_id": -sort_order,
            "case_name": self._short_text(case_name, 128),
            "case_version": self._version(),
            "snapshot_json": {
                "case_type": "MANUAL",
                "manual": True,
                "generated": True,
                "description": self._case_description(
                    requirement_item,
                    scenario,
                ),
                "steps": self._string_list(scenario.get("steps")),
                "expected": str(scenario.get("expected") or ""),
                "knowledge_id": principle_id,
                "knowledge_key": str(data.get("knowledge_key") or ""),
                "knowledge_name": principle_name,
                "requirement_title": requirement_title,
                "requirement_item": requirement_item,
            },
            "sort_order": sort_order,
        }

    def _create_plan(
        self,
        payload: KnowledgePlanGenerationRequest,
        principles: list[dict[str, object]],
        requirement_item_count: int,
        generated_count: int,
    ) -> ExecutionPlan:
        knowledge_ids = [int(item["id"]) for item in principles]
        knowledge_keys = [
            str(self._object_value(item.get("data")).get("knowledge_key") or "")
            for item in principles
        ]
        return self.plan_repository.create(
            {
                "name": payload.plan_name,
                "project_id": payload.project_id,
                "test_rounds": payload.test_rounds,
                "test_type": ExecutionPlanTestTypeEnum.WEB.code,
                "description": f"基于《{payload.requirement_title}》和 {len(principles)} 项测试原则生成。",
                "requirement_title": payload.requirement_title,
                "requirement_document": payload.requirement_document,
                "generation_json": {
                    "source": "knowledge_requirement",
                    "knowledge_ids": knowledge_ids,
                    "knowledge_keys": knowledge_keys,
                    "requirement_item_count": requirement_item_count,
                    "generated_case_count": generated_count,
                },
                "status": ExecutionPlanStatusEnum.ACTIVE.code,
            }
        )

    def _persist_case_rows(
        self,
        plan_id: int,
        rows: list[dict[str, object]],
    ) -> None:
        payloads = [{"plan_id": plan_id, **row} for row in rows]
        self.plan_repository.create_plan_cases(payloads)

    def _object_value(self, value: object) -> dict[str, object]:
        return value if isinstance(value, dict) else {}

    def _string_list(self, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if str(item).strip()]

    def _case_description(
        self,
        requirement_item: str,
        scenario: dict[str, object],
    ) -> str:
        objective = str(scenario.get("objective") or "")
        expected = str(scenario.get("expected") or "")
        return (
            f"需求点：{requirement_item}\n"
            f"测试目标：{objective}\n"
            f"预期结果：{expected}"
        )

    def _short_text(self, value: str, max_length: int) -> str:
        normalized = " ".join(value.split())
        return normalized[:max_length]

    def _version(self) -> str:
        return datetime.now(UTC).isoformat(timespec="seconds")
