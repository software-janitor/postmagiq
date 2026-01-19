"""Custom SQLAlchemy types with SQLite-friendly fallbacks."""

from __future__ import annotations

from typing import Any, Iterable, Optional
from uuid import UUID

from sqlalchemy import JSON
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import TypeDecorator


class JsonOrArray(TypeDecorator):
    """Use Postgres ARRAY when available, JSON elsewhere."""

    cache_ok = True
    impl = JSON

    def __init__(self, item_type: Any):
        super().__init__()
        self.item_type = item_type

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.ARRAY(self.item_type))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value: Optional[Iterable[Any]], dialect):
        if value is None:
            return None
        if dialect.name != "postgresql":
            return [str(item) if isinstance(item, UUID) else item for item in value]
        return list(value)

    def process_result_value(self, value: Optional[Iterable[Any]], dialect):
        if value is None:
            return None
        if dialect.name != "postgresql" and isinstance(self.item_type, postgresql.UUID):
            return [UUID(str(item)) for item in value]
        return list(value)


class JsonOrVector(TypeDecorator):
    """Use pgvector on Postgres, JSON elsewhere."""

    cache_ok = True
    impl = JSON

    def __init__(self, dimensions: int):
        super().__init__()
        self.dimensions = dimensions

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from pgvector.sqlalchemy import Vector

            return dialect.type_descriptor(Vector(self.dimensions))
        return dialect.type_descriptor(JSON())

