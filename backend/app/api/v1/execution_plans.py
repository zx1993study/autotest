"""Execution plan endpoints backed by the dedicated execution_plans table."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import page_result, success
from app.db.session import get_db
from app.repositories.sqlalchemy_execution_plan_repository import (
    SqlAlchemyExecutionPlanRepository,
)
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.schemas.common import BatchDeleteRequest
from app.schemas.execution import (
    ExecutionPlanCreate,
    ExecutionPlanListQuery,
    ExecutionPlanUpdate,
)
from app.services.execution_plan_configuration_service import (
    ExecutionPlanConfigurationService,
)
from app.services.execution_plan_service import ExecutionPlanService


router = APIRouter(prefix="/execution/plans", tags=["execution-plans"])


def get_execution_plan_service(
    db: Session = Depends(get_db),
) -> ExecutionPlanService:
    """Provide execution plan behavior without exposing database sessions."""

    return ExecutionPlanService(SqlAlchemyExecutionPlanRepository(db))


def get_execution_plan_configuration_service(
    db: Session = Depends(get_db),
) -> ExecutionPlanConfigurationService:
    """Provide validated plan configuration across plan and resource stores."""

    return ExecutionPlanConfigurationService(
        SqlAlchemyExecutionPlanRepository(db),
        SqlAlchemyResourceRepository(db),
    )


@router.get("")
def list_execution_plans(
    query: ExecutionPlanListQuery = Depends(),
    service: ExecutionPlanService = Depends(get_execution_plan_service),
) -> dict[str, object]:
    items, total = service.list(
        keyword=query.keyword,
        project_id=query.project_id,
        test_type=query.test_type.code if query.test_type else None,
        status=query.status.code if query.status else None,
        page=query.page,
        page_size=query.page_size,
    )
    return page_result([item.model_dump(mode="json") for item in items], total, query.page, query.page_size)


@router.post("")
def create_execution_plan(
    payload: ExecutionPlanCreate,
    service: ExecutionPlanConfigurationService = Depends(
        get_execution_plan_configuration_service
    ),
) -> dict[str, object]:
    return success(service.create(payload).model_dump(mode="json"))


@router.post("/batch-delete")
def batch_delete_execution_plans(
    payload: BatchDeleteRequest,
    service: ExecutionPlanService = Depends(get_execution_plan_service),
) -> dict[str, object]:
    return success(service.batch_delete(payload.ids))


@router.get("/{plan_id:int}")
def get_execution_plan(
    plan_id: int,
    service: ExecutionPlanService = Depends(get_execution_plan_service),
) -> dict[str, object]:
    return success(service.get(plan_id).model_dump(mode="json"))


@router.put("/{plan_id:int}")
def update_execution_plan(
    plan_id: int,
    payload: ExecutionPlanUpdate,
    service: ExecutionPlanConfigurationService = Depends(
        get_execution_plan_configuration_service
    ),
) -> dict[str, object]:
    return success(service.update(plan_id, payload).model_dump(mode="json"))


@router.delete("/{plan_id:int}")
def delete_execution_plan(
    plan_id: int,
    service: ExecutionPlanService = Depends(get_execution_plan_service),
) -> dict[str, object]:
    return success(service.delete(plan_id))
