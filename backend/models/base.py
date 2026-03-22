import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models (SQLAlchemy 2.0 style)."""
    
    def __repr__(self) -> str:
        """Generic __repr__ that shows class name and primary key(s)."""
        cls = self.__class__.__name__
        primary_keys = self.__mapper__.primary_key
        pk_info = ", ".join(f"{pk.name}={getattr(self, pk.name)!r}" for pk in primary_keys)
        return f"{cls}({pk_info})"

class TimestampMixin:
    """Mixin for models that need created_at and updated_at timestamps."""
    
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )
