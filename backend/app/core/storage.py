from __future__ import annotations

import os
from pathlib import Path


LEGACY_STORAGE_ROOT = Path(__file__).resolve().parents[2] / "storage"


def storage_path(*parts: str) -> Path:
    """Keep runtime data outside releases when a persistent root is configured."""
    configured = os.environ.get("AUTOTEST_STORAGE_DIR", "").strip()
    root = Path(os.path.expandvars(configured)).expanduser() if configured else LEGACY_STORAGE_ROOT
    return root.resolve().joinpath(*parts)

