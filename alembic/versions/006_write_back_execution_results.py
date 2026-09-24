"""Add execution_results to write_back_proposals."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "write_back_proposals",
        sa.Column(
            "execution_results",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )
    op.alter_column("write_back_proposals", "execution_results", server_default=None)


def downgrade() -> None:
    op.drop_column("write_back_proposals", "execution_results")
