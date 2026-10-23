"""Company history marker and medicine load time (data-freshness and coverage in the UI).

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("company", sa.Column("history_fetched_at", sa.DateTime(timezone=True)))
    op.add_column(
        "medicine",
        sa.Column(
            "fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_column("medicine", "fetched_at")
    op.drop_column("company", "history_fetched_at")
