"""Exercise existing batch deletion through HTTP against a disposable database."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_resource_repository
from app.api.v1.api_case_drafts import router
from app.db.base import Base
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.case_draft_service import CaseDraftService


def test_delete_mixed_status_drafts_keeps_adopted_cases_and_is_idempotent():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    try:
        with sessionmaker(bind=engine)() as session:
            repository = SqlAlchemyResourceRepository(session)
            service = CaseDraftService("API", repository)
            drafts = [service.create({"name": f"draft-{index}", "project_id": 1, "source_id": 30}) for index in range(3)]
            adopted = service.accept(drafts[1]["id"])
            service.reject(drafts[2]["id"], "mock rejection")
            app = FastAPI()
            app.include_router(router)
            app.dependency_overrides[get_resource_repository] = lambda: repository
            ids = [item["id"] for item in drafts]
            with TestClient(app) as client:
                result = client.post("/api-testing/case-drafts/batch-delete", json={"ids": ids + [ids[0], 999999]})
                assert result.json()["data"]["deleted_count"] == 3
                assert repository.get("api_test_cases", adopted["id"]) is not None
                result = client.post("/api-testing/case-drafts/batch-delete", json={"ids": ids})
                assert result.json()["data"]["deleted_count"] == 0
                assert client.get("/api-testing/case-drafts").json()["data"]["total"] == 0
                assert client.post("/api-testing/case-drafts/batch-delete", json={"ids": []}).status_code == 422
    finally:
        engine.dispose()
