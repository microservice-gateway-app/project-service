from __future__ import annotations

import uuid
from typing import Any
from uuid import uuid4

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_serializer,
    model_validator,
)


class UUID(BaseModel, frozen=True):
    value: str = Field(default_factory=lambda: str(uuid4()), frozen=True)

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: str):
        try:
            uuid.UUID(value)
            return value
        except ValueError:
            raise ValueError(f"Value must be UUID, got {value}")

    @model_serializer
    def serialize(self) -> str:
        return self.value

    @model_validator(mode="before")
    @classmethod
    def validate_input(cls, data: Any) -> dict[str, Any]:
        """
        Handle parsing from string or dict input during model creation.
        """
        if isinstance(data, str):
            return {"value": cls.validate_value(data)}
        elif isinstance(data, dict):
            if "value" in data:
                d = dict[str, Any](**data)
                return {"value": cls.validate_value(d["value"])}
            return {}
        raise TypeError(
            f"Expected a string or dict with key 'value', got {type(data).__name__}"
        )

    class Config:
        @classmethod
        def json_schema_extra(cls, schema: dict[str, Any]) -> None:
            """Modify schema to represent as a string."""
            schema.clear()  # Clear the default schema
            schema.update({"type": "string", "example": str(uuid4())})
