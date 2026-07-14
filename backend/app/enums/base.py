"""Enumeration base classes with storage codes and display descriptions."""

from enum import Enum

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema


class DescribedStrEnum(str, Enum):
    """String enum that validates by code and serializes as description.

    Codes remain stable for persistence and request validation. Pydantic JSON
    serialization uses the human-readable description so output schemas do not
    leak storage-oriented values into the UI contract.
    """

    _description: str

    def __new__(cls, code: str, description: str) -> "DescribedStrEnum":
        member = str.__new__(cls, code)
        member._value_ = code
        member._description = description
        return member

    @property
    def code(self) -> str:
        """Return the persistence and request-validation value."""

        return str(self.value)

    @property
    def desc(self) -> str:
        """Return the display value exposed by output schemas."""

        return self._description

    def __str__(self) -> str:
        """Preserve the storage code when legacy code calls ``str(enum)``."""

        return self.code

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: type["DescribedStrEnum"],
        handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        """Attach description-based JSON serialization to Pydantic schemas."""

        schema = handler(source_type)
        schema["serialization"] = core_schema.plain_serializer_function_ser_schema(
            lambda value: value.desc,
            return_schema=core_schema.str_schema(),
            when_used="json",
        )
        return schema


class DescribedIntEnum(int, Enum):
    """Integer enum carrying a stable error code and display description."""

    _description: str

    def __new__(cls, code: int, description: str) -> "DescribedIntEnum":
        member = int.__new__(cls, code)
        member._value_ = code
        member._description = description
        return member

    @property
    def code(self) -> int:
        """Return the numeric API error code."""

        return int(self.value)

    @property
    def desc(self) -> str:
        """Return the default client-facing error description."""

        return self._description
