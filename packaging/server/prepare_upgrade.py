"""Back up a deployment and copy persistent files before a release switch."""
from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import make_url


def database_backup(environment, destination):
    values = dotenv_values(environment)
    url = make_url(values["DATABASE_URL"]) if values.get("DATABASE_URL") else None
    credentials = {
        "host": url.host if url else values.get("MYSQL_HOST", "127.0.0.1"),
        "port": str(url.port or 3306) if url else values.get("MYSQL_PORT", "3306"),
        "user": url.username if url else values.get("MYSQL_USER", "root"),
        "password": url.password if url else values.get("MYSQL_PASSWORD", ""),
    }
    database = url.database if url else values.get("MYSQL_DATABASE", "autotest")
    client = destination / "mysql-client.cnf"
    try:
        with client.open("x", encoding="utf-8") as handle:
            os.chmod(client, 0o600)
            handle.write("[client]\n")
            for key, value in credentials.items():
                escaped = str(value or "").replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
                handle.write(f'{key}="{escaped}"\n')
        snapshot = destination / "database.sql"
        with snapshot.open("xb") as output:
            os.chmod(snapshot, 0o600)
            subprocess.run(["mysqldump", f"--defaults-extra-file={client}", "--single-transaction", "--no-tablespaces", "--skip-lock-tables", database], stdout=output, check=True)
    finally:
        client.unlink(missing_ok=True)


def prepare(base, release, incoming):
    old = (base / "current").resolve(strict=True)
    if old.parent != base / "releases" or release.parent != base / "releases":
        raise ValueError("Unexpected release path")
    backup = base / "backups" / release.name
    backup.mkdir(parents=True, exist_ok=False)
    os.chmod(backup, 0o700)
    for name in ("backend/.env", "run-backend.sh"):
        source = old / name
        if source.is_file():
            target = backup / source.name
            shutil.copy2(source, target)
            os.chmod(target, 0o600)
    with tarfile.open(backup / "runtime-storage.tar.gz", "w:gz") as archive:
        for name in ("backend/storage", "backend/app/storage"):
            if (old / name).is_dir():
                archive.add(old / name, arcname=name)
    database_backup(old / "backend/.env", backup)
    shared = base / "shared"
    shared.mkdir(exist_ok=True)
    os.chmod(shared, 0o700)
    configuration = shared / "platform.env"
    if not configuration.exists():
        shutil.copy2(old / "backend/.env", configuration)
    os.chmod(configuration, 0o600)
    if len(dotenv_values(configuration).get("AUTH_SECRET_KEY", "")) < 32:
        raise ValueError("Existing JWT signing key must be migrated unchanged")
    module_path = release / "scripts/migrate_runtime_storage.py"
    spec = importlib.util.spec_from_file_location("storage_upgrade", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for source in (old / "backend/storage", old / "backend/app/storage", incoming):
        if source and source.is_dir():
            report = module.migrate(source, shared / "storage", apply=True)
            print(f"Migrated {source.name}: {report['copied']} new, {report['unchanged']} identical")
    print(f"Backup completed: {backup}; original release and database schema unchanged")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--incoming", type=Path)
    args = parser.parse_args()
    prepare(args.base.resolve(), args.release.resolve(), args.incoming.resolve() if args.incoming else None)


if __name__ == "__main__":
    main()
