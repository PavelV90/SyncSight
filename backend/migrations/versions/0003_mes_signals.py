"""MES-signal sources: building permits, licence changes, medicines, websites, web hits.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-23
"""

from collections.abc import Sequence
from datetime import datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _fetched_at(name: str = "fetched_at") -> sa.Column[datetime]:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


def upgrade() -> None:
    op.create_table(
        "building_permit",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_uid", sa.String(15), primary_key=True),
        sa.Column("publication_number", sa.Text(), nullable=False),
        sa.Column("publication_date", sa.Date(), nullable=False),
        sa.Column("sub_rubric", sa.String(12), nullable=False),
        sa.Column("cantons", sa.Text()),
        sa.Column("municipality", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("location", sa.Text()),
        sa.Column("applicant_name", sa.Text(), nullable=False),
        _fetched_at(),
    )
    op.create_index(
        "ix_building_permit_company_date", "building_permit", ["company_uid", "publication_date"]
    )

    op.create_table(
        "swissmedic_site_change",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("detected_on", sa.Date(), nullable=False),
        sa.Column("licence_number", sa.Text(), nullable=False),
        sa.Column("site_number", sa.Text(), nullable=False),
        sa.Column("company_uid", sa.String(15)),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text()),
    )
    op.create_index(
        "ix_swissmedic_site_change_company_uid", "swissmedic_site_change", ["company_uid"]
    )

    op.create_table(
        "medicine",
        sa.Column("authorisation_number", sa.Text(), primary_key=True),
        sa.Column("product_name", sa.Text(), nullable=False),
        sa.Column("usage", sa.String(8)),
        sa.Column("atc_code", sa.Text()),
        sa.Column("status", sa.String(4)),
        sa.Column("first_authorised_on", sa.Date()),
        sa.Column("holder_name", sa.Text()),
        sa.Column("holder_name_key", sa.Text()),
        sa.Column("holder_postal_code", sa.String(10)),
        sa.Column("company_uid", sa.String(15)),
    )
    op.create_index("ix_medicine_holder_name_key", "medicine", ["holder_name_key"])
    op.create_index("ix_medicine_company_uid", "medicine", ["company_uid"])

    op.create_table(
        "company_website",
        sa.Column("company_uid", sa.String(15), primary_key=True),
        sa.Column("url", sa.Text()),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("evidence", sa.Text()),
        _fetched_at("checked_at"),
    )

    op.create_table(
        "web_hit",
        sa.Column("company_uid", sa.String(15), primary_key=True),
        sa.Column("url", sa.Text(), primary_key=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("title", sa.Text()),
        sa.Column("published_on", sa.Date()),
        sa.Column("keywords", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("snippet", sa.Text()),
        _fetched_at(),
    )


def downgrade() -> None:
    for table in (
        "web_hit",
        "company_website",
        "medicine",
        "swissmedic_site_change",
        "building_permit",
    ):
        op.drop_table(table)
