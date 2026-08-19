"""add transfer sessions and items

Revision ID: 0002_transfer_sessions
Revises: 0001_initial
Create Date: 2026-08-18 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_transfer_sessions"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transfer_sessions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("owner_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_code", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_code", name="uq_transfer_sessions_session_code"),
    )
    op.create_index("ix_transfer_sessions_owner_id", "transfer_sessions", ["owner_id"], unique=False)
    op.create_index("ix_transfer_sessions_session_code", "transfer_sessions", ["session_code"], unique=True)

    op.create_table(
        "transfer_items",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", sa.Uuid(as_uuid=True), sa.ForeignKey("transfer_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_name", sa.String(length=512), nullable=False),
        sa.Column("stored_name", sa.String(length=512), nullable=True),
        sa.Column("storage_path", sa.String(length=1024), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_transfer_items_session_id", "transfer_items", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_transfer_items_session_id", table_name="transfer_items")
    op.drop_table("transfer_items")

    op.drop_index("ix_transfer_sessions_session_code", table_name="transfer_sessions")
    op.drop_index("ix_transfer_sessions_owner_id", table_name="transfer_sessions")
    op.drop_table("transfer_sessions")
