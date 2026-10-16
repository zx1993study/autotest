"""Custom actions for system principles and requirement-based plan generation."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_resource_repository
from app.core.response import success
from app.db.session import get_db
from app.repositories.interfaces import ResourceRepository
from app.repositories.sqlalchemy_execution_plan_repository import (
    SqlAlchemyExecutionPlanRepository,
)
from app.repositories.sqlalchemy_resource_repository import (
    SqlAlchemyResourceRepository,
)
from app.schemas.knowledge import (
    KnowledgePlanGenerationRequest,
    SeedKnowledgeRequest,
)
from app.services.knowledge_plan_generation_service import (
    KnowledgePlanGenerationService,
)
from app.services.knowledge_seed_service import KnowledgeSeedService


router = APIRouter(prefix="/project-knowledge", tags=["project-knowledge"])


def get_knowledge_seed_service(
    repository: ResourceRepository = Depends(get_resource_repository),
) -> KnowledgeSeedService:
    """Provide system-principle synchronization behavior."""

    return KnowledgeSeedService(repository)


def get_knowledge_plan_generation_service(
    db: Session = Depends(get_db),
) -> KnowledgePlanGenerationService:
    """Provide cross-resource plan generation with explicit dependencies."""

    return KnowledgePlanGenerationService(
        SqlAlchemyResourceRepository(db),
        SqlAlchemyExecutionPlanRepository(db),
    )


@router.post("/seed-defaults")
def seed_default_knowledge(
    payload: SeedKnowledgeRequest,
    service: KnowledgeSeedService = Depends(get_knowledge_seed_service),
) -> dict[str, object]:
    """Synchronize the eight system-managed test principles."""

    return success(service.seed_defaults(payload.project_id, payload.overwrite))


@router.post("/generate-plan")
def generate_execution_plan(
    payload: KnowledgePlanGenerationRequest,
    service: KnowledgePlanGenerationService = Depends(
        get_knowledge_plan_generation_service
    ),
) -> dict[str, object]:
    """Generate and persist a Web execution plan from a page requirement."""

    return success(service.generate(payload).model_dump(mode="json"))
