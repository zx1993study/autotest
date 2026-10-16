"""Snapshot shared configuration, storage and the database before a release switch."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import tarfile
from datetime import UTC, datetime
from pathlib import Path

from prepare_upgrade import database_backup


def backup_release(base: Path, version: str) -> Path:
    if not re.fullmatch(r"[a-zA-Z0-9.-]+", version) or version in {".", ".."}:
        raise ValueError("Invalid release version")
    base = base.resolve(strict=True)
    current = (base / "current").resolve(strict=True)
    if current.parent != (base / "releases").resolve(strict=True):
        raise ValueError("Current release is outside the release directory")
    shared = base / "shared"
    environment = shared / "platform.env"
    storage = shared / "storage"
    if not environment.is_file() or not storage.is_dir():
        raise ValueError("Shared configuration or storage is missing")
    destination = base / "backups" / version
    destination.mkdir(parents=True, exist_ok=False, mode=0o700)
    os.chmod(destination, 0o700)
    configuration = destination / "platform.env"
    shutil.copy2(environment, configuration)
    os.chmod(configuration, 0o600)
    snapshot = destination / "runtime-storage.tar.gz"
    with snapshot.open("xb") as handle:
        os.chmod(snapshot, 0o600)
        with tarfile.open(fileobj=handle, mode="w:gz") as archive:
            archive.add(storage, arcname="storage")
    database_backup(environment, destination)
    manifest = destination / "release.json"
    manifest.write_text(json.dumps({
        "previous_release": str(current),
        "next_version": version,
        "created_at": datetime.now(UTC).isoformat(),
        "database_schema_changed": False,
    }, indent=2) + "\n", encoding="utf-8")
    os.chmod(manifest, 0o600)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    print(f"Release backup completed: {backup_release(args.base, args.version)}")


if __name__ == "__main__":
    main()
