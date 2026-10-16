from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.repositories.sqlalchemy_execution_plan_repository import (
    SqlAlchemyExecutionPlanRepository,
)


class SqlAlchemyExecutionPlanRepositoryTest(unittest.TestCase):
    def test_create_should_persist_requirement_generation_fields(self) -> None:
        engine = create_engine("sqlite+pysqlite:///:memory:")
        try:
            Base.metadata.create_all(engine)
            with Session(engine) as session:
                repository = SqlAlchemyExecutionPlanRepository(session)

                created = repository.create(
                    {
                        "name": "仓库新增计划",
                        "project_id": 8,
                        "test_rounds": 1,
                        "test_type": "WEB",
                        "description": "由需求生成",
                        "requirement_title": "仓库新增页面",
                        "requirement_document": "填写仓库名称并选择管理员后保存。",
                        "generation_json": {
                            "source": "knowledge_requirement",
                            "generated_case_count": 3,
                        },
                        "api_ids_json": [12, 13],
                        "web_feature_ids_json": [21],
                        "status": "active",
                    }
                )

                loaded = repository.get(created.id)

                self.assertIsNotNone(loaded)
                self.assertEqual(loaded.requirement_title, "仓库新增页面")
                self.assertEqual(
                    loaded.generation_json["generated_case_count"],
                    3,
                )
                self.assertEqual(loaded.api_ids_json, [12, 13])
                self.assertEqual(loaded.web_feature_ids_json, [21])
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
