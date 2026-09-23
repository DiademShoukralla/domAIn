"""Add council_decision to chat_messages and write_back_proposals table."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "chat_messages",
        sa.Column("council_decision", postgresql.JSONB(), nullable=True),
    )

    op.create_table(
        "write_back_proposals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "chat_message_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan", postgresql.JSONB(), nullable=False),
        sa.Column(
            "feedback_history",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="proposed"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_write_back_proposals_chat_message_id",
        "write_back_proposals",
        ["chat_message_id"],
        unique=True,
    )
    op.create_index("ix_write_back_proposals_user_id", "write_back_proposals", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_write_back_proposals_user_id", table_name="write_back_proposals")
    op.drop_index("ix_write_back_proposals_chat_message_id", table_name="write_back_proposals")
    op.drop_table("write_back_proposals")
    op.drop_column("chat_messages", "council_decision")
