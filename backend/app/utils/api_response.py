"""Read business response metadata without confusing it with HTTP status."""

import json
from typing import Any

from app.core.types import JsonValue


def extract_response_code(body: Any) -> JsonValue:
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except (ValueError, TypeError):
            return None
    return body.get("code") if isinstance(body, dict) else None
