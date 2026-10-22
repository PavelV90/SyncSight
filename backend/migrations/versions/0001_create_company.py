"""Create company table with full-text search vector.

Revision ID: 0001
Revises:
Create Date: 2026-10-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "company",
        sa.Column("uid", sa.String(15), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("legal_form", sa.String(4)),
        sa.Column("seat", sa.Text()),
        sa.Column("canton", sa.String(2)),
        sa.Column("status", sa.Text()),
        sa.Column("purpose", sa.Text()),
        sa.Column("capital_nominal", sa.Numeric(18, 2)),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(
                "to_tsvector('simple', coalesce(name, '') || ' ' || coalesce(purpose, ''))",
                persisted=True,
            ),
        ),
    )
    op.create_index(
        "ix_company_search_vector", "company", ["search_vector"], postgresql_using="gin"
    )


def downgrade() -> None:
    op.drop_index("ix_company_search_vector", table_name="company")
    op.drop_table("company")
