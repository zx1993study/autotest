"""Custom execution plan actions with action-specific dependencies."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import success
from app.db.session import get_db
from app.repositories.sqlalchemy_execution_plan_repository import (
    SqlAlchemyExecutionPlanRepository,
)
from app.repositories.sqlalchemy_resource_repository import (
    SqlAlchemyResourceRepository,
)
from app.schemas.execution import (
    ExecutionPlanFeatureAddRequest,
    ExecutionPlanManualFeatureCreate,
    ExecutionPlanRunRequest,
)
from app.services.execution_plan_generation_service import (
    ExecutionPlanGenerationService,
)
from app.services.execution_plan_run_service import ExecutionPlanRunService
from app.services.execution_plan_service import ExecutionPlanService


router = APIRouter(prefix="/execution/plans", tags=["execution-plan-actions"])


def get_execution_plan_service(db: Session = Depends(get_db)) -> ExecutionPlanService:
    """Provide detail and lifecycle behavior."""

    return ExecutionPlanService(SqlAlchemyExecutionPlanRepository(db))


def get_execution_plan_run_service(db: Session = Depends(get_db)) -> ExecutionPlanRunService:
    """Provide run orchestration with plan and resource stores."""

    return ExecutionPlanRunService(
        SqlAlchemyExecutionPlanRepository(db),
        SqlAlchemyResourceRepository(db),
    )


def get_execution_plan_generation_service(
    db: Session = Depends(get_db),
) -> ExecutionPlanGenerationService:
    """Provide knowledge and source based plan generation."""

    return ExecutionPlanGenerationService(
        SqlAlchemyExecutionPlanRepository(db),
        SqlAlchemyResourceRepository(db),
    )


@router.get("/{plan_id:int}/detail")
def get_execution_plan_detail(
    plan_id: int,
    service: ExecutionPlanService = Depends(get_execution_plan_service),
) -> dict[str, object]:
    return success(service.detail(plan_id).model_dump(mode="json"))


@router.post("/{plan_id:int}/generate")
def generate_execution_plan_cases(
    plan_id: int,
    service: ExecutionPlanGenerationService = Depends(
        get_execution_plan_generation_service
    ),
) -> dict[str, object]:
    return success(service.generate(plan_id).model_dump(mode="json"))


@router.post("/{plan_id:int}/features")
def add_execution_plan_features(
    plan_id: int,
    payload: ExecutionPlanFeatureAddRequest,
    service: ExecutionPlanService = Depends(get_execution_plan_service),
) -> dict[str, object]:
    return success(service.add_features(plan_id, payload).model_dump(mode="json"))


@router.post("/{plan_id:int}/manual-features")
def add_execution_plan_manual_feature(
    plan_id: int,
    payload: ExecutionPlanManualFeatureCreate,
    service: ExecutionPlanService = Depends(get_execution_plan_service),
) -> dict[str, object]:
    return success(service.add_manual_feature(plan_id, payload).model_dump(mode="json"))


@router.post("/{plan_id:int}/complete")
def complete_execution_plan(
    plan_id: int,
    service: ExecutionPlanService = Depends(get_execution_plan_service),
) -> dict[str, object]:
    return success(service.complete(plan_id).model_dump(mode="json"))


@router.post("/{plan_id:int}/run")
def run_execution_plan(
    plan_id: int,
    payload: ExecutionPlanRunRequest,
    service: ExecutionPlanRunService = Depends(get_execution_plan_run_service),
) -> dict[str, object]:
    return success(service.run(plan_id, payload).model_dump(mode="json"))


@router.post("/{plan_id:int}/copy")
def copy_execution_plan(
    plan_id: int,
    service: ExecutionPlanService = Depends(get_execution_plan_service),
) -> dict[str, object]:
    return success(service.copy(plan_id).model_dump(mode="json"))
