"""Parse page requirement documents into bounded, testable requirement items."""

from __future__ import annotations

import re


MAX_REQUIREMENT_ITEMS = 20
MAX_REQUIREMENT_ITEM_LENGTH = 500
LIST_PREFIX_PATTERN = re.compile(r"^\s*(?:[-*•]+|\d+[.、)])\s*")
ITEM_SEPARATOR_PATTERN = re.compile(r"(?:\r?\n)+|[。；;]+")


class RequirementDocumentParser:
    """Convert semi-structured requirement text into unique test targets."""

    def parse(self, document: str) -> list[str]:
        """Return at most twenty normalized items to prevent plan explosion."""

        candidates = ITEM_SEPARATOR_PATTERN.split(document)
        items: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            normalized = self._normalize_item(candidate)
            if not normalized or normalized in seen:
                continue
            items.append(normalized)
            seen.add(normalized)
            if len(items) >= MAX_REQUIREMENT_ITEMS:
                break
        return items or [document.strip()[:MAX_REQUIREMENT_ITEM_LENGTH]]

    def _normalize_item(self, value: str) -> str:
        without_prefix = LIST_PREFIX_PATTERN.sub("", value)
        normalized = " ".join(without_prefix.split()).strip()
        return normalized[:MAX_REQUIREMENT_ITEM_LENGTH]
