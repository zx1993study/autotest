from __future__ import annotations

from sqlalchemy import bindparam, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.models import execution_plan  # noqa: F401
from app.models import resource_record  # noqa: F401
from app.models import test_case_record  # noqa: F401
from app.repositories.sqlalchemy_resource_repository import SqlAlchemyResourceRepository
from app.services.ai_prompt_seed_service import AiPromptSeedService
from app.services.auth_service import AuthService
from app.services.dictionary_seed_service import DictionarySeedService
from app.services.knowledge_seed_service import KnowledgeSeedService
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

    try:
        with engine.connect():
            return
    except OperationalError as exc:
        if not exc.orig.args or exc.orig.args[0] != 1049:
            raise

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
        if settings.auto_create_schema:
            # Compatibility mode for existing local installations. Production
            # deployments should disable this and run Alembic migrations.
            ensure_database_exists()
            ensure_schema_compatibility()
            seed_default_data()
        else:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
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


def ensure_schema_compatibility() -> None:
    if not make_url(settings.database_url).drivername.startswith("mysql"):
        Base.metadata.create_all(bind=engine)
        return
    tables = Base.metadata.sorted_tables
    table_names = tuple(table.name for table in tables)
    with engine.begin() as connection:
        columns = _mysql_column_names(connection, table_names)
        existing = {table_name for table_name, _ in columns}
        missing = [table for table in tables if table.name not in existing]
        if missing:
            Base.metadata.create_all(bind=connection, tables=missing)
            columns = _mysql_column_names(connection, table_names)
        _add_strategy_columns(connection, columns)
        _add_execution_plan_columns(connection, columns)
        _ensure_resource_record_indexes(connection)


def ensure_test_case_strategy_columns() -> None:
    url = make_url(settings.database_url)
    if not url.drivername.startswith("mysql"):
        return
    table_names = ("api_test_cases", "web_test_cases", "app_test_cases", "miniapp_test_cases")
    with engine.begin() as connection:
        columns = _mysql_column_names(connection, table_names)
        _add_strategy_columns(connection, columns)


def _add_strategy_columns(connection, columns: set[tuple[str, str]]) -> None:
    for table_name in ("api_test_cases", "web_test_cases", "app_test_cases", "miniapp_test_cases"):
        if (table_name, "strategy_ids_json") not in columns:
            connection.execute(
                text(
                    f"ALTER TABLE {_quote_mysql_identifier(table_name)} "
                    "ADD COLUMN strategy_ids_json JSON NULL"
                )
            )


def ensure_execution_plan_requirement_columns() -> None:
    """Keep existing MySQL installations compatible with generated plans."""

    url = make_url(settings.database_url)
    if not url.drivername.startswith("mysql"):
        return
    with engine.begin() as connection:
        existing = _mysql_column_names(connection, ("execution_plans",))
        _add_execution_plan_columns(connection, existing)


def _add_execution_plan_columns(connection, existing: set[tuple[str, str]]) -> None:
    columns = {
        "requirement_title": "VARCHAR(128) NULL",
        "requirement_document": "TEXT NULL",
        "generation_json": "JSON NULL",
        "api_ids_json": "JSON NULL",
        "web_feature_ids_json": "JSON NULL",
    }
    for column_name, column_type in columns.items():
        if ("execution_plans", column_name) not in existing:
            safe_column_name = _quote_mysql_identifier(column_name)
            connection.execute(
                text(
                    "ALTER TABLE `execution_plans` "
                    f"ADD COLUMN {safe_column_name} {column_type}"
                )
            )


def _mysql_column_names(connection, table_names: tuple[str, ...]) -> set[tuple[str, str]]:
    query = text(
        "SELECT TABLE_NAME, COLUMN_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN :table_names"
    ).bindparams(bindparam("table_names", expanding=True))
    rows = connection.execute(query, {"table_names": table_names})
    return {(row[0], row[1]) for row in rows}


def ensure_resource_record_indexes() -> None:
    """Add indexes missed by older create_all-based local installations."""

    url = make_url(settings.database_url)
    if not url.drivername.startswith("mysql"):
        return
    with engine.begin() as connection:
        _ensure_resource_record_indexes(connection)


def _ensure_resource_record_indexes(connection) -> None:
    exists = connection.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = 'resource_records' "
            "AND INDEX_NAME = 'ix_resource_table_status_deleted'"
        )
    ).scalar()
    if not exists:
        connection.execute(
            text(
                "CREATE INDEX ix_resource_table_status_deleted "
                "ON resource_records (table_name, status, deleted)"
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
        knowledge_service = KnowledgeSeedService(repository)
        projects, _ = repository.list("projects", page=1, page_size=10000)
        for project in projects:
            project_id = project.get("id")
            if isinstance(project_id, int):
                knowledge_service.seed_defaults(project_id, overwrite=False)
    finally:
        db.close()
