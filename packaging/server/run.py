"""Start a server release with configuration and data outside the checkout."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def configure(shared, root):
    from dotenv import dotenv_values

    environment = shared / "platform.env"
    if not environment.is_file():
        raise ValueError("Missing shared/platform.env; migrate the existing server configuration first")
    for key, value in dotenv_values(environment).items():
        if value is not None:
            os.environ.setdefault(key, value)
    secret = os.environ.get("AUTH_SECRET_KEY", "")
    if len(secret) < 32 or secret.startswith("change-me"):
        raise ValueError("A persistent AUTH_SECRET_KEY of at least 32 characters is required")
    os.environ["AUTO_CREATE_SCHEMA"] = "false"
    os.environ["AUTOTEST_STORAGE_DIR"] = str(shared / "storage")
    os.environ["AUTOTEST_FRONTEND_DIST"] = str(root / "frontend" / "dist")
    os.environ.setdefault("LOG_DIR", str(shared / "logs"))
    sys.path.insert(0, str(root / "backend"))
    sys.path.insert(0, str(root / "web_automation" / "src"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shared-dir", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    configure(args.shared_dir.resolve(), root)
    import uvicorn

    uvicorn.run("app.main:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
