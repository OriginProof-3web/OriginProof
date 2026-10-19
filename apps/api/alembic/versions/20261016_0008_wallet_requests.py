"""Add request conflict protection and bounded verification sessions."""

import sqlalchemy as sa
from alembic import op

revision = "20261016_0008"
down_revision = "20261015_0007"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "wallet_request_claims",
        sa.Column(
            "account_id", sa.String(64), sa.ForeignKey("accounts.account_id"), primary_key=True
        ),
        sa.Column("action", sa.String(32), primary_key=True),
        sa.Column("request_id", sa.String(128), primary_key=True),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(128), nullable=False),
    )
    op.create_table(
        "wallet_verification_sessions",
        sa.Column("session_id", sa.String(64), primary_key=True),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
    )


def downgrade():
    op.drop_table("wallet_verification_sessions")
    op.drop_table("wallet_request_claims")
