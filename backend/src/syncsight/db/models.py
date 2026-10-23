"""SQLAlchemy models. Schema changes go through Alembic migrations."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Computed,
    Date,
    DateTime,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# 'simple' = no language-specific stemming; register texts mix DE/FR/IT/EN.
SEARCH_CONFIG = "simple"


class Base(DeclarativeBase):
    pass


class Company(Base):
    """Snapshot of a legal entity from Zefix (via LINDAS), keyed by UID (CHE-xxx.xxx.xxx)."""

    __tablename__ = "company"

    uid: Mapped[str] = mapped_column(String(15), primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    name_key: Mapped[str | None] = mapped_column(Text, index=True)
    legal_form: Mapped[str | None] = mapped_column(String(4))
    seat: Mapped[str | None] = mapped_column(Text)
    canton: Mapped[str | None] = mapped_column(String(2))
    municipality_id: Mapped[int | None] = mapped_column(Integer)
    street: Mapped[str | None] = mapped_column(Text)
    postal_code: Mapped[str | None] = mapped_column(String(10))
    locality: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(Text)
    purpose: Mapped[str | None] = mapped_column(Text)
    capital_nominal: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    source: Mapped[str | None] = mapped_column(Text)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            f"to_tsvector('{SEARCH_CONFIG}', coalesce(name, '') || ' ' || coalesce(purpose, ''))",
            persisted=True,
        ),
    )

    __table_args__ = (Index("ix_company_search_vector", "search_vector", postgresql_using="gin"),)


class SogcNotice(Base):
    """A commercial-register notice (rubric HR) from SHAB/SOGC: the company event log.

    publication_text names natural persons; it is stored for rule-based parsing but is
    never full-text indexed (no search by person name, see ARCHITECTURE.md).
    """

    __tablename__ = "sogc_notice"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    publication_number: Mapped[str] = mapped_column(Text, unique=True)
    publication_date: Mapped[date] = mapped_column(Date, index=True)
    sub_rubric: Mapped[str] = mapped_column(String(8))
    language: Mapped[str | None] = mapped_column(String(2))
    cantons: Mapped[str | None] = mapped_column(Text)
    company_uid: Mapped[str | None] = mapped_column(String(15))
    company_name: Mapped[str | None] = mapped_column(Text)
    company_seat: Mapped[str | None] = mapped_column(Text)
    legal_form: Mapped[str | None] = mapped_column(String(4))
    purpose: Mapped[str | None] = mapped_column(Text)
    capital_nominal: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    changes: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default="{}")
    publication_text: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_sogc_notice_company_date", "company_uid", "publication_date"),
        Index("ix_sogc_notice_changes", "changes", postgresql_using="gin"),
    )


class SwissmedicSite(Base):
    """One site of a Swissmedic establishment licence (medicinal products incl. blood)."""

    __tablename__ = "swissmedic_site"

    licence_number: Mapped[str] = mapped_column(Text, primary_key=True)
    site_number: Mapped[str] = mapped_column(Text, primary_key=True)
    holder_name: Mapped[str] = mapped_column(Text)
    holder_name_key: Mapped[str] = mapped_column(Text, index=True)
    holder_street: Mapped[str | None] = mapped_column(Text)
    holder_postal_code: Mapped[str | None] = mapped_column(String(10))
    holder_locality: Mapped[str | None] = mapped_column(Text)
    holder_canton: Mapped[str | None] = mapped_column(String(2))
    valid_until: Mapped[str | None] = mapped_column(Text)
    site_name: Mapped[str | None] = mapped_column(Text)
    site_street: Mapped[str | None] = mapped_column(Text)
    site_postal_code: Mapped[str | None] = mapped_column(String(10))
    site_locality: Mapped[str | None] = mapped_column(Text)
    site_canton: Mapped[str | None] = mapped_column(String(2))
    certificate_number: Mapped[str | None] = mapped_column(Text)
    last_inspection: Mapped[date | None] = mapped_column(Date)
    compliance_status: Mapped[str | None] = mapped_column(Text)
    activity_codes: Mapped[list[int]] = mapped_column(ARRAY(SmallInteger), server_default="{}")
    activity_details: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    company_uid: Mapped[str | None] = mapped_column(String(15), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BuildingPermit(Base):
    """A building-permit notice (cantonal gazettes on amtsblattportal.ch) filed by a company.

    Only company applicants are stored; notices filed by natural persons are dropped at parse time.
    """

    __tablename__ = "building_permit"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    company_uid: Mapped[str] = mapped_column(String(15), primary_key=True)
    publication_number: Mapped[str] = mapped_column(Text)
    publication_date: Mapped[date] = mapped_column(Date)
    sub_rubric: Mapped[str] = mapped_column(String(12))
    cantons: Mapped[str | None] = mapped_column(Text)
    municipality: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(Text)
    applicant_name: Mapped[str] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_building_permit_company_date", "company_uid", "publication_date"),)


class SwissmedicSiteChange(Base):
    """Difference between two Swissmedic licence snapshots (site, activity or compliance)."""

    __tablename__ = "swissmedic_site_change"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    detected_on: Mapped[date] = mapped_column(Date)
    licence_number: Mapped[str] = mapped_column(Text)
    site_number: Mapped[str] = mapped_column(Text)
    company_uid: Mapped[str | None] = mapped_column(String(15), index=True)
    kind: Mapped[str] = mapped_column(Text)
    detail: Mapped[str | None] = mapped_column(Text)


class Medicine(Base):
    """An authorised medicinal product (Swissmedic open data), linked to its holder company."""

    __tablename__ = "medicine"

    authorisation_number: Mapped[str] = mapped_column(Text, primary_key=True)
    product_name: Mapped[str] = mapped_column(Text)
    usage: Mapped[str | None] = mapped_column(String(8))
    atc_code: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String(4))
    first_authorised_on: Mapped[date | None] = mapped_column(Date)
    holder_name: Mapped[str | None] = mapped_column(Text)
    holder_name_key: Mapped[str | None] = mapped_column(Text, index=True)
    holder_postal_code: Mapped[str | None] = mapped_column(String(10))
    company_uid: Mapped[str | None] = mapped_column(String(15), index=True)


class CompanyWebsite(Base):
    """A company's website and how it was found or verified."""

    __tablename__ = "company_website"

    company_uid: Mapped[str] = mapped_column(String(15), primary_key=True)
    url: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)  # lindas | wikidata | verified-guess | manual | none
    evidence: Mapped[str | None] = mapped_column(Text)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WebHit(Base):
    """A company web page or feed item whose text matched MES-signal keywords.

    Only URL, title, date, matched keywords and a short snippet are kept, never the page text.
    """

    __tablename__ = "web_hit"

    company_uid: Mapped[str] = mapped_column(String(15), primary_key=True)
    url: Mapped[str] = mapped_column(Text, primary_key=True)
    kind: Mapped[str] = mapped_column(Text)  # feed | news | career | page
    title: Mapped[str | None] = mapped_column(Text)
    published_on: Mapped[date | None] = mapped_column(Date)
    keywords: Mapped[list[str]] = mapped_column(ARRAY(Text))
    snippet: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
