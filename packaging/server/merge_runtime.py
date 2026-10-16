"""Merge an upgrade's runtime files, backing up mutable configuration conflicts."""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
from pathlib import Path

DIRECTORIES = {"auth", "ai-secrets", "ai-task-details", "screenshots", "app-recordings"}
MUTABLE = {"auth", "ai-secrets"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def merge(incoming, destination, original, backup):
    incoming, destination, original, backup = (Path(item).resolve() for item in (incoming, destination, original, backup))
    if len({incoming, destination, original, backup}) != 4:
        raise ValueError("Merge directories must be distinct")
    planned, updated, preserved = [], 0, 0
    for source in incoming.rglob("*"):
        if source.is_symlink():
            raise ValueError("Symlinks cannot be migrated")
        if not source.is_file():
            continue
        relative = source.relative_to(incoming)
        if relative.parts[0] not in DIRECTORIES:
            raise ValueError("Unexpected runtime directory")
        target = destination / relative
        if not target.resolve().is_relative_to(destination):
            raise ValueError("Runtime destination escaped")
        if target.exists() and digest(source) != digest(target):
            if relative.parts[0] not in MUTABLE:
                raise ValueError(f"Immutable evidence conflict: {relative}")
            old = original / relative
            old_time = old.stat().st_mtime if old.is_file() else target.stat().st_mtime
            if source.stat().st_mtime <= old_time:
                preserved += 1
                continue
        elif target.exists():
            preserved += 1
            continue
        planned.append((source, target, relative))
    for source, target, relative in planned:
        if target.exists():
            saved = backup / relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if os.name != "nt":
            os.chmod(target, 0o600)
        if digest(source) != digest(target):
            raise ValueError("Runtime copy verification failed")
        updated += 1
    return {"updated": updated, "preserved": preserved}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("incoming", "destination", "original", "backup"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    print(merge(args.incoming, args.destination, args.original, args.backup))
