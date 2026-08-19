"""add burn after download and download count to transfer_sessions

Revision ID: 0003_burn_after_download
Revises: 0002_transfer_sessions
Create Date: 2026-08-18 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_burn_after_download"
down_revision = "0002_transfer_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "transfer_sessions",
        sa.Column("burn_after_download", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "transfer_sessions",
        sa.Column("download_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("transfer_sessions", "download_count")
    op.drop_column("transfer_sessions", "burn_after_download")
