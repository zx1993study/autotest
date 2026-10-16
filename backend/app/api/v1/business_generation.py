from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_resource_repository
from app.core.response import success
from app.repositories.interfaces import ResourceRepository
from app.scheduler.jobs.business_generation_jobs import submit_generation_job
from app.scheduler.jobs.web_vision_jobs import submit_server_vision
from app.schemas.ai import WebVisionDiscoveryRequest
from app.schemas.business_generation import GenerationRequest
from app.services.business_generation_service import BusinessGenerationService
from app.services.web_vision_agent_service import WebVisionAgentService
from app.services.web_vision_discovery_service import WebVisionDiscoveryService

RepositoryDependency = Annotated[ResourceRepository, Depends(get_resource_repository)]
router = APIRouter(tags=["business-generation"])


def submit(domain, payload, repository):
    task = BusinessGenerationService(repository).submit(domain, payload)
    submit_generation_job(task["id"])
    return success({"task_id": task["id"], "status": "queued"})


@router.post("/api-testing/generation")
def api_generation(payload: GenerationRequest, repository: RepositoryDependency):
    return submit("API", payload, repository)


@router.post("/web-testing/generation")
def web_generation(payload: GenerationRequest, repository: RepositoryDependency):
    return submit("WEB", payload, repository)


@router.post("/app-testing/generation")
def app_generation(payload: GenerationRequest, repository: RepositoryDependency):
    return submit("APP", payload, repository)


@router.post("/web-testing/vision-discovery")
def vision_discovery(payload: WebVisionDiscoveryRequest, repository: RepositoryDependency):
    if not payload.headless:
        return success(WebVisionAgentService(repository).queue(payload))
    service = WebVisionDiscoveryService(repository)
    if payload.dry_run:
        return success(service.discover(payload))
    submitted = service.submit(payload)
    submit_server_vision(int(submitted["task_id"]), payload)
    return success(submitted)
