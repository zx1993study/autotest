from pydantic import BaseModel


class SeedKnowledgeRequest(BaseModel):
    project_id: int | None = None
    overwrite: bool = False
