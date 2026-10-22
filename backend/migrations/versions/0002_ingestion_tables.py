"""Ingestion tables: Zefix snapshot columns, SOGC notices, Swissmedic sites.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-22
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COMPANY_COLUMNS: list[sa.Column[Any]] = [
    sa.Column("name_key", sa.Text()),
    sa.Column("municipality_id", sa.Integer()),
    sa.Column("street", sa.Text()),
    sa.Column("postal_code", sa.String(10)),
    sa.Column("locality", sa.Text()),
    sa.Column("source", sa.Text()),
    sa.Column("last_seen_at", sa.DateTime(timezone=True)),
]


def upgrade() -> None:
    for column in _COMPANY_COLUMNS:
        op.add_column("company", column)
    op.create_index("ix_company_name_key", "company", ["name_key"])

    op.create_table(
        "sogc_notice",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("publication_number", sa.Text(), nullable=False, unique=True),
        sa.Column("publication_date", sa.Date(), nullable=False),
        sa.Column("sub_rubric", sa.String(8), nullable=False),
        sa.Column("language", sa.String(2)),
        sa.Column("cantons", sa.Text()),
        sa.Column("company_uid", sa.String(15)),
        sa.Column("company_name", sa.Text()),
        sa.Column("company_seat", sa.Text()),
        sa.Column("legal_form", sa.String(4)),
        sa.Column("purpose", sa.Text()),
        sa.Column("capital_nominal", sa.Numeric(18, 2)),
        sa.Column("changes", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("publication_text", sa.Text()),
        sa.Column(
            "fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_sogc_notice_publication_date", "sogc_notice", ["publication_date"])
    op.create_index(
        "ix_sogc_notice_company_date", "sogc_notice", ["company_uid", "publication_date"]
    )
    op.create_index("ix_sogc_notice_changes", "sogc_notice", ["changes"], postgresql_using="gin")

    op.create_table(
        "swissmedic_site",
        sa.Column("licence_number", sa.Text(), primary_key=True),
        sa.Column("site_number", sa.Text(), primary_key=True),
        sa.Column("holder_name", sa.Text(), nullable=False),
        sa.Column("holder_name_key", sa.Text(), nullable=False),
        sa.Column("holder_street", sa.Text()),
        sa.Column("holder_postal_code", sa.String(10)),
        sa.Column("holder_locality", sa.Text()),
        sa.Column("holder_canton", sa.String(2)),
        sa.Column("valid_until", sa.Text()),
        sa.Column("site_name", sa.Text()),
        sa.Column("site_street", sa.Text()),
        sa.Column("site_postal_code", sa.String(10)),
        sa.Column("site_locality", sa.Text()),
        sa.Column("site_canton", sa.String(2)),
        sa.Column("certificate_number", sa.Text()),
        sa.Column("last_inspection", sa.Date()),
        sa.Column("compliance_status", sa.Text()),
        sa.Column(
            "activity_codes",
            postgresql.ARRAY(sa.SmallInteger()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("activity_details", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("company_uid", sa.String(15)),
        sa.Column(
            "fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_swissmedic_site_holder_name_key", "swissmedic_site", ["holder_name_key"])
    op.create_index("ix_swissmedic_site_company_uid", "swissmedic_site", ["company_uid"])


def downgrade() -> None:
    op.drop_table("swissmedic_site")
    op.drop_table("sogc_notice")
    op.drop_index("ix_company_name_key", table_name="company")
    for column in reversed(_COMPANY_COLUMNS):
        op.drop_column("company", column.name)
