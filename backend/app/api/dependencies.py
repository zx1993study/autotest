"""Dependency providers used by API routers."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.interfaces import ApiModuleRepository, ResourceRepository
from app.repositories.sqlalchemy_api_module_repository import (
    SqlAlchemyApiModuleRepository,
)
from app.repositories.sqlalchemy_resource_repository import (
    SqlAlchemyResourceRepository,
)


def get_resource_repository(
    db: Session = Depends(get_db),
) -> ResourceRepository:
    """Provide the persistence abstraction without exposing Session to routers."""

    return SqlAlchemyResourceRepository(db)


def get_api_module_repository(db: Session = Depends(get_db)) -> ApiModuleRepository:
    return SqlAlchemyApiModuleRepository(db)
