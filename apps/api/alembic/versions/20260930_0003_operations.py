"""Add operation reservations and request-scoped deduplication.

Revision ID: 20260930_0003
Revises: 20260930_0002
"""

import sqlalchemy as sa
from alembic import op

revision = "20260930_0003"
down_revision = "20260930_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operations",
        sa.Column("operation_id", sa.String(64), primary_key=True),
        sa.Column(
            "account_id", sa.String(64), sa.ForeignKey("accounts.account_id"), nullable=False
        ),
        sa.Column("issuer_id", sa.String(128)),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("request_id", sa.String(128), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("tx_hash", sa.String(66)),
        sa.Column("error_code", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("account_id", "action", "request_id"),
    )


def downgrade() -> None:
    op.drop_table("operations")
