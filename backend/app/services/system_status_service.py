"""System readiness queries used by health endpoints."""

from app.db.init_db import database_status, try_init_db


class SystemStatusService:
    """Expose infrastructure readiness without leaking DB calls into routers."""

    def database_status(self) -> dict[str, str | bool]:
        """Attempt initialization and return a password-masked status payload."""

        try_init_db()
        return database_status()
