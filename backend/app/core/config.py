"""Validated application settings loaded from environment variables."""

from pathlib import Path
from urllib.parse import quote_plus


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
ENV_FILE = BACKEND_DIR / ".env"


def _mysql_database_url(
    host: str,
    port: int,
    user: str,
    password: str,
    database: str,
) -> str:
    """Build a URL while escaping credentials that may contain URL symbols."""

    credentials = quote_plus(user)
    if password:
        credentials = f"{credentials}:{quote_plus(password)}"
    return (
        f"mysql+pymysql://{credentials}@{host}:{port}/{database}"
        "?charset=utf8mb4&connect_timeout=3"
    )


try:
    from pydantic import Field
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class Settings(BaseSettings):
        """Application settings backed by pydantic-settings."""

        model_config = SettingsConfigDict(
            env_file=ENV_FILE,
            env_file_encoding="utf-8",
            case_sensitive=False,
            extra="ignore",
        )

        database_url_override: str | None = Field(
            default=None,
            validation_alias="DATABASE_URL",
        )
        mysql_host: str = "127.0.0.1"
        mysql_port: int = 3306
        mysql_user: str = "root"
        mysql_password: str = ""
        mysql_database: str = "autotest"
        cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
        auto_create_schema: bool = True
        log_dir: Path = PROJECT_ROOT / "logs"
        log_level: str = "INFO"
        auth_secret_key: str = "change-me-local-autotest-secret"
        auth_access_token_expire_minutes: int = 480
        default_admin_username: str = "admin"
        default_admin_password: str = "Admin@123456"

        @property
        def database_url(self) -> str:
            """Return the explicit URL or build one from validated MySQL fields."""

            return self.database_url_override or _mysql_database_url(
                self.mysql_host,
                self.mysql_port,
                self.mysql_user,
                self.mysql_password,
                self.mysql_database,
            )

        @property
        def allowed_origins(self) -> list[str]:
            """Return normalized CORS origins without empty entries."""

            return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

        @property
        def resolved_log_dir(self) -> Path:
            """Return an absolute log directory path."""

            return self.log_dir if self.log_dir.is_absolute() else (BACKEND_DIR / self.log_dir).resolve()

except ModuleNotFoundError:
    # This compatibility path keeps local development operational until the
    # declared pydantic-settings dependency is installed.
    from pydantic.v1 import BaseSettings, Field

    class Settings(BaseSettings):
        """Compatibility settings with the same public contract."""

        database_url_override: str | None = Field(default=None, env="DATABASE_URL")
        mysql_host: str = "127.0.0.1"
        mysql_port: int = 3306
        mysql_user: str = "root"
        mysql_password: str = ""
        mysql_database: str = "autotest"
        cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
        auto_create_schema: bool = True
        log_dir: Path = PROJECT_ROOT / "logs"
        log_level: str = "INFO"
        auth_secret_key: str = "change-me-local-autotest-secret"
        auth_access_token_expire_minutes: int = 480
        default_admin_username: str = "admin"
        default_admin_password: str = "Admin@123456"

        class Config:
            """Pydantic v1 environment-loading configuration."""

            env_file = ENV_FILE
            env_file_encoding = "utf-8"
            case_sensitive = False

        @property
        def database_url(self) -> str:
            """Return the explicit URL or build one from validated MySQL fields."""

            return self.database_url_override or _mysql_database_url(
                self.mysql_host,
                self.mysql_port,
                self.mysql_user,
                self.mysql_password,
                self.mysql_database,
            )

        @property
        def allowed_origins(self) -> list[str]:
            """Return normalized CORS origins without empty entries."""

            return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

        @property
        def resolved_log_dir(self) -> Path:
            """Return an absolute log directory path."""

            return self.log_dir if self.log_dir.is_absolute() else (BACKEND_DIR / self.log_dir).resolve()


settings = Settings()
