from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import unittest

from app.constants.knowledge_principles import DEFAULT_KNOWLEDGE_ITEMS
from app.core.exceptions import BusinessRuleError
from app.models.execution_plan import ExecutionPlan
from app.schemas.knowledge import KnowledgePlanGenerationRequest
from app.services.knowledge_plan_generation_service import (
    KnowledgePlanGenerationService,
)
from app.services.requirement_document_parser import RequirementDocumentParser


class FakeKnowledgeRepository:
    """Read-only knowledge repository used by generation tests."""

    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = {int(row["id"]): row for row in rows}

    def get(self, table: str, item_id: int) -> dict[str, object] | None:
        return self.rows.get(item_id) if table == "project_knowledge" else None


class FakePlanRepository:
    """Capture generated plans and snapshots without a database."""

    def __init__(self, fail_case_write: bool = False) -> None:
        self.plan: ExecutionPlan | None = None
        self.case_rows: list[dict[str, object]] = []
        self.deleted_ids: list[int] = []
        self.fail_case_write = fail_case_write

    def create(self, data: dict[str, object]) -> ExecutionPlan:
        now = datetime(2026, 7, 28, 10, 0, 0)
        self.plan = ExecutionPlan(
            id=41,
            name=str(data["name"]),
            project_id=int(data["project_id"]),
            test_rounds=int(data["test_rounds"]),
            test_type=str(data["test_type"]),
            description=str(data["description"]),
            requirement_title=str(data["requirement_title"]),
            requirement_document=str(data["requirement_document"]),
            generation_json=data["generation_json"],
            status=str(data["status"]),
            deleted=False,
            created_at=now,
            updated_at=now,
        )
        return self.plan

    def create_plan_cases(self, rows: list[dict[str, object]]) -> list[object]:
        if self.fail_case_write:
            raise RuntimeError("case write failed")
        self.case_rows.extend(deepcopy(rows))
        return []

    def delete(self, plan_id: int) -> bool:
        self.deleted_ids.append(plan_id)
        return True


def principle_row(index: int, project_id: int = 8) -> dict[str, object]:
    """Build one active project principle from the maintained defaults."""

    item = deepcopy(DEFAULT_KNOWLEDGE_ITEMS[index])
    return {
        "id": index + 1,
        "project_id": project_id,
        "status": "active",
        **item,
    }


def generation_payload(principle_ids: list[int]) -> KnowledgePlanGenerationRequest:
    """Build a valid page requirement payload for service tests."""

    return KnowledgePlanGenerationRequest(
        project_id=8,
        plan_name="仓库新增测试计划",
        requirement_title="仓库新增页面",
        requirement_document="用户填写仓库名称、仓库地址并选择管理员后保存仓库。",
        principle_ids=principle_ids,
        test_rounds=2,
    )


class KnowledgePlanGenerationServiceTest(unittest.TestCase):
    def test_generate_should_persist_requirement_and_principle_scenarios(self) -> None:
        knowledge_repository = FakeKnowledgeRepository(
            [principle_row(0), principle_row(1)]
        )
        plan_repository = FakePlanRepository()
        service = KnowledgePlanGenerationService(
            knowledge_repository,
            plan_repository,
        )

        result = service.generate(generation_payload([1, 2]))

        self.assertEqual(result.plan_id, 41)
        self.assertEqual(result.generated_case_count, 6)
        self.assertEqual(len(plan_repository.case_rows), 6)
        self.assertEqual(plan_repository.plan.requirement_title, "仓库新增页面")
        self.assertEqual(plan_repository.case_rows[0]["case_type"], "MANUAL")
        snapshot = plan_repository.case_rows[0]["snapshot_json"]
        self.assertIsInstance(snapshot, dict)
        self.assertEqual(snapshot["knowledge_id"], 1)
        self.assertIn("仓库名称", snapshot["requirement_item"])

    def test_generate_should_reject_principle_from_another_project(self) -> None:
        knowledge_repository = FakeKnowledgeRepository([principle_row(0, 9)])
        service = KnowledgePlanGenerationService(
            knowledge_repository,
            FakePlanRepository(),
        )

        with self.assertRaisesRegex(BusinessRuleError, "其它项目"):
            service.generate(generation_payload([1]))

    def test_generate_should_remove_plan_when_case_persistence_fails(self) -> None:
        plan_repository = FakePlanRepository(fail_case_write=True)
        service = KnowledgePlanGenerationService(
            FakeKnowledgeRepository([principle_row(0)]),
            plan_repository,
        )

        with self.assertRaisesRegex(RuntimeError, "case write failed"):
            service.generate(generation_payload([1]))

        self.assertEqual(plan_repository.deleted_ids, [41])

    def test_requirement_parser_should_split_and_deduplicate_items(self) -> None:
        parser = RequirementDocumentParser()

        items = parser.parse(
            "1. 支持仓库名称查询。\n2. 支持新增仓库；支持仓库名称查询。"
        )

        self.assertEqual(items, ["支持仓库名称查询", "支持新增仓库"])


if __name__ == "__main__":
    unittest.main()
