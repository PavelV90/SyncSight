"""SQLAlchemy models. Schema changes go through Alembic migrations."""

from decimal import Decimal

from sqlalchemy import Computed, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# 'simple' = no language-specific stemming; register texts mix DE/FR/IT/EN.
SEARCH_CONFIG = "simple"


class Base(DeclarativeBase):
    pass


class Company(Base):
    """A legal entity from the commercial register, keyed by its UID (CHE-xxx.xxx.xxx)."""

    __tablename__ = "company"

    uid: Mapped[str] = mapped_column(String(15), primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    legal_form: Mapped[str | None] = mapped_column(String(4))
    seat: Mapped[str | None] = mapped_column(Text)
    canton: Mapped[str | None] = mapped_column(String(2))
    status: Mapped[str | None] = mapped_column(Text)
    purpose: Mapped[str | None] = mapped_column(Text)
    capital_nominal: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            f"to_tsvector('{SEARCH_CONFIG}', coalesce(name, '') || ' ' || coalesce(purpose, ''))",
            persisted=True,
        ),
    )

    __table_args__ = (Index("ix_company_search_vector", "search_vector", postgresql_using="gin"),)
