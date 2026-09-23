"""GitHub App installation fields on connections."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("connections", sa.Column("installation_id", sa.String(length=64), nullable=True))
    op.alter_column("connections", "access_token", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    op.alter_column("connections", "access_token", existing_type=sa.Text(), nullable=False)
    op.drop_column("connections", "installation_id")
