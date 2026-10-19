"""V2 issued proofs and server-only recipient binding material; preserves v1."""

import sqlalchemy as sa
from alembic import op

revision = "20261001_0005"
down_revision = "20261001_0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "recipient_tokens",
        sa.Column(
            "account_id", sa.String(64), sa.ForeignKey("accounts.account_id"), primary_key=True
        ),
        sa.Column("token", sa.String(64), nullable=False),
    )
    op.create_table(
        "finals_proofs",
        sa.Column("proof_id", sa.String(128), primary_key=True),
        sa.Column(
            "account_id", sa.String(64), sa.ForeignKey("accounts.account_id"), nullable=False
        ),
        sa.Column("issuer_id", sa.String(128), nullable=False),
        sa.Column("key_id", sa.String(128), nullable=False),
        sa.Column("request_id", sa.String(128), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column(
            "recipient_account_id",
            sa.String(64),
            sa.ForeignKey("accounts.account_id"),
            nullable=False,
        ),
        sa.Column("recipient_salt", sa.String(64), nullable=False),
        sa.Column("target_ref", sa.String(500)),
        sa.Column("deployment_id", sa.String(68), nullable=False),
        sa.Column("envelope", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("account_id", "request_id"),
    )
    op.create_index("ix_finals_proofs_issuer_id", "finals_proofs", ["issuer_id"])


def downgrade():
    op.drop_table("finals_proofs")
    op.drop_table("recipient_tokens")
