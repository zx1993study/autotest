from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.exceptions import InfrastructureUnavailableError


database_url = make_url(settings.database_url)
connect_args = (
    {"check_same_thread": False}
    if database_url.drivername.startswith("sqlite")
    else {}
)
if database_url.drivername.startswith("mysql"):
    connect_args.setdefault("connect_timeout", 3)

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=3600,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    from app.db.init_db import database_status, ensure_initialized

    if not ensure_initialized(raise_on_error=False):
        status_data = database_status()
        raise InfrastructureUnavailableError(str(status_data["message"]))

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
