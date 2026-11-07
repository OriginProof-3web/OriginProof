"""Bind optional issuance results to analysis without giving the analyzer authority."""

import sqlalchemy as sa
from alembic import op

revision = "20261016_0009"
down_revision = "20261016_0008"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("wallet_analyses", sa.Column("verification_result", sa.JSON(), nullable=True))
    op.add_column(
        "wallet_verification_sessions",
        sa.Column("account_id", sa.String(64), sa.ForeignKey("accounts.account_id"), nullable=True),
    )
    op.add_column(
        "wallet_verification_sessions",
        sa.Column("privacy_scope", sa.String(16), server_default="LEGACY", nullable=False),
    )
    op.alter_column("wallet_verification_sessions", "privacy_scope", server_default=None)


def downgrade():
    op.drop_column("wallet_verification_sessions", "privacy_scope")
    op.drop_column("wallet_verification_sessions", "account_id")
    op.drop_column("wallet_analyses", "verification_result")
