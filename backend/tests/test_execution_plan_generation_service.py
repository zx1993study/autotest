from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError
from app.db.base import Base
from app.repositories.sqlalchemy_execution_plan_repository import (
    SqlAlchemyExecutionPlanRepository,
)
from app.repositories.sqlalchemy_resource_repository import (
    SqlAlchemyResourceRepository,
)
from app.schemas.execution import ExecutionPlanCreate
from app.services.execution_plan_configuration_service import (
    ExecutionPlanConfigurationService,
)
from app.services.execution_plan_generation_service import (
    ExecutionPlanGenerationService,
)


class ExecutionPlanGenerationServiceTest(unittest.TestCase):
    """Verify configured sources produce idempotent executable snapshots."""

    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.resources = SqlAlchemyResourceRepository(self.session)
        self.plans = SqlAlchemyExecutionPlanRepository(self.session)
        self._seed_resources()

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

    def test_generate_should_update_existing_cases_without_duplication(self) -> None:
        plan = ExecutionPlanConfigurationService(
            self.plans,
            self.resources,
        ).create(
            ExecutionPlanCreate(
                name="仓库综合计划",
                project_id=self.project_id,
                api_ids=[self.api_id],
                web_feature_ids=[self.web_page_id],
            )
        )
        service = ExecutionPlanGenerationService(self.plans, self.resources)

        first = service.generate(plan.id)
        second = service.generate(plan.id)
        api_cases, api_total = self.resources.list(
            "api_test_cases",
            project_id=self.project_id,
            page_size=10000,
        )
        web_cases, web_total = self.resources.list(
            "web_test_cases",
            project_id=self.project_id,
            page_size=10000,
        )

        self.assertEqual(first.generated_case_count, 4)
        self.assertEqual(second.generated_case_count, 4)
        self.assertEqual(api_total, 2)
        self.assertEqual(web_total, 2)
        self.assertEqual(second.detail.summary.case_count, 4)
        self.assertTrue(all(item["status"] == "active" for item in [*api_cases, *web_cases]))

    def test_configuration_should_reject_source_from_another_project(self) -> None:
        other_project = self.resources.create(
            "projects",
            {"name": "其它项目", "status": "active"},
        )
        foreign_api = self.resources.create(
            "api_interfaces",
            {
                "name": "其它接口",
                "project_id": other_project["id"],
                "status": "active",
                "data": {"method": "GET", "path": "/other"},
            },
        )

        with self.assertRaisesRegex(BusinessRuleError, "不属于当前项目"):
            ExecutionPlanConfigurationService(self.plans, self.resources).create(
                ExecutionPlanCreate(
                    name="非法计划",
                    project_id=self.project_id,
                    api_ids=[int(foreign_api["id"])],
                )
            )

    def test_generate_should_not_expand_an_unselected_domain(self) -> None:
        plan = ExecutionPlanConfigurationService(
            self.plans,
            self.resources,
        ).create(
            ExecutionPlanCreate(
                name="API 专项计划",
                project_id=self.project_id,
                api_ids=[self.api_id],
            )
        )

        result = ExecutionPlanGenerationService(
            self.plans,
            self.resources,
        ).generate(plan.id)

        self.assertEqual(result.api_case_count, 2)
        self.assertEqual(result.web_case_count, 0)
        self.assertEqual(
            [group.case_type for group in result.detail.groups],
            ["API"],
        )

    def _seed_resources(self) -> None:
        project = self.resources.create(
            "projects",
            {"name": "默认项目", "status": "active", "data": {"is_default": True}},
        )
        self.project_id = int(project["id"])
        interface = self.resources.create(
            "api_interfaces",
            {
                "name": "仓库新增",
                "project_id": self.project_id,
                "status": "active",
                "data": {"method": "POST", "path": "/warehouses"},
            },
        )
        self.api_id = int(interface["id"])
        self.resources.create(
            "api_fields",
            {
                "name": "name",
                "project_id": self.project_id,
                "status": "active",
                "data": {
                    "interface_id": self.api_id,
                    "name": "name",
                    "location": "body",
                    "required": True,
                    "field_type": "string",
                },
            },
        )
        page = self.resources.create(
            "web_pages",
            {
                "name": "仓库新增页面",
                "project_id": self.project_id,
                "status": "active",
                "data": {"route": "/warehouses/create"},
            },
        )
        self.web_page_id = int(page["id"])
        self.resources.create(
            "web_elements",
            {
                "name": "仓库名称",
                "project_id": self.project_id,
                "status": "active",
                "data": {
                    "page_id": self.web_page_id,
                    "element_type": "input",
                    "locator": "#warehouse-name",
                    "required": True,
                },
            },
        )
        self.resources.create(
            "project_knowledge",
            {
                "name": "边界测试",
                "project_id": self.project_id,
                "status": "active",
                "data": {
                    "kind": "test_principle",
                    "domain": "COMMON",
                    "category": "boundary",
                    "knowledge_key": "principle.boundary_testing",
                },
            },
        )


if __name__ == "__main__":
    unittest.main()
