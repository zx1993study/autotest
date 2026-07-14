from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.models import resource_record  # noqa: F401
from app.models import test_case_record  # noqa: F401
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.ai_prompt_seed_service import AiPromptSeedService
from app.services.auth_service import AuthService
from app.services.dictionary_seed_service import DictionarySeedService
from app.services.test_case_migration_service import TestCaseMigrationService


_initialized = False
_last_error: str | None = None


def _quote_mysql_identifier(identifier: str) -> str:
    return f"`{identifier.replace('`', '``')}`"


def _database_error_message(exc: Exception) -> str:
    return (
        "MySQL 数据库连接失败，请检查 backend/.env 或 DATABASE_URL。"
        "需要可访问的 MYSQL_HOST/MYSQL_PORT/MYSQL_USER/"
        f"MYSQL_PASSWORD/MYSQL_DATABASE。当前错误：{exc}"
    )


def ensure_database_exists() -> None:
    url = make_url(settings.database_url)
    if not url.drivername.startswith("mysql") or not url.database:
        return

    server_url = url._replace(database=None)
    bootstrap_engine = create_engine(
        server_url,
        pool_pre_ping=True,
        isolation_level="AUTOCOMMIT",
        connect_args={"connect_timeout": 3},
    )
    try:
        database_name = _quote_mysql_identifier(url.database)
        with bootstrap_engine.connect() as connection:
            connection.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS {database_name} "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
    finally:
        bootstrap_engine.dispose()


def ensure_initialized(raise_on_error: bool = True) -> bool:
    global _initialized, _last_error

    if _initialized:
        return True
    try:
        ensure_database_exists()
        if settings.auto_create_schema:
            # Compatibility mode for existing local installations. Production
            # deployments should disable this and run Alembic migrations.
            Base.metadata.create_all(bind=engine)
            ensure_test_case_strategy_columns()
        seed_default_data()
    except SQLAlchemyError as exc:
        _last_error = _database_error_message(exc)
        if raise_on_error:
            raise RuntimeError(_last_error) from exc
        return False
    _initialized = True
    _last_error = None
    return True


def database_status() -> dict[str, str | bool]:
    safe_url = make_url(settings.database_url).render_as_string(hide_password=True)
    return {
        "ready": _initialized,
        "database_url": safe_url,
        "schema_management": "create_all" if settings.auto_create_schema else "alembic",
        "message": _last_error or "MySQL 数据库连接正常",
    }


def init_db() -> None:
    ensure_initialized(raise_on_error=True)


def try_init_db() -> bool:
    return ensure_initialized(raise_on_error=False)


def ensure_test_case_strategy_columns() -> None:
    url = make_url(settings.database_url)
    if not url.drivername.startswith("mysql"):
        return
    table_names = ("api_test_cases", "web_test_cases", "app_test_cases", "miniapp_test_cases")
    with engine.begin() as connection:
        for table_name in table_names:
            exists = connection.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() "
                    "AND TABLE_NAME = :table_name "
                    "AND COLUMN_NAME = 'strategy_ids_json'"
                ),
                {"table_name": table_name},
            ).scalar()
            if not exists:
                connection.execute(
                    text(
                        f"ALTER TABLE {_quote_mysql_identifier(table_name)} "
                        "ADD COLUMN strategy_ids_json JSON NULL"
                    )
                )


def seed_default_data() -> None:
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        repository = SqlAlchemyResourceRepository(db)
        AuthService(repository).ensure_default_admin()
        DictionarySeedService(repository).seed_playwright_defaults(overwrite=False)
        AiPromptSeedService(repository).seed_defaults(overwrite=False)
        TestCaseMigrationService(repository).migrate_legacy_test_cases()
    finally:
        db.close()
