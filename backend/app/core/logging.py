from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configure_logging(log_dir: Path, log_level: str) -> None:
    """Configure application and server logs under one directory.

    The application is started in several ways during local development. A
    central file handler keeps FastAPI, scheduler jobs, and uvicorn logs in the
    same ``logs`` directory regardless of the launch script.
    """

    root_logger = logging.getLogger()
    if getattr(root_logger, "_autotest_logging_configured", False):
        return

    log_dir.mkdir(parents=True, exist_ok=True)
    level = getattr(logging, log_level.upper(), logging.INFO)
    formatter = logging.Formatter(LOG_FORMAT)
    file_handler = RotatingFileHandler(
        log_dir / "backend.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    setattr(file_handler, "_autotest_managed", True)

    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        logger.addHandler(file_handler)
        logger.propagate = False

    setattr(root_logger, "_autotest_logging_configured", True)
