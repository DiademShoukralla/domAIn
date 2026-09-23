"""Add project_id to write_back_proposals."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "write_back_proposals",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_write_back_proposals_project_id",
        "write_back_proposals",
        ["project_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_write_back_proposals_project_id", table_name="write_back_proposals")
    op.drop_column("write_back_proposals", "project_id")
