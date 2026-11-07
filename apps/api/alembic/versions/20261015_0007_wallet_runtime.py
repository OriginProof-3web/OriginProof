"""Add wallet storage without reinterpreting legacy rows."""

import sqlalchemy as sa
from alembic import op

revision = "20261015_0007"
down_revision = "20261003_0006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "wallet_onboarding",
        sa.Column(
            "application_id",
            sa.String(length=64),
            sa.ForeignKey("issuer_applications.application_id"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("code_hash", sa.String(length=128), nullable=True),
        sa.Column("demo_code", sa.String(length=6), nullable=True),
        sa.Column("code_expires_at", sa.BigInteger(), nullable=False),
        sa.Column("issued_at", sa.BigInteger(), nullable=False),
        sa.Column("issues", sa.JSON(), nullable=False),
        sa.Column("failures", sa.JSON(), nullable=False),
        sa.Column("code_failures", sa.Integer(), nullable=False),
        sa.Column("email_verified", sa.Boolean(), nullable=False),
        sa.Column("internally_approved", sa.Boolean(), nullable=False),
        sa.Column(
            "approved_by", sa.String(length=64), sa.ForeignKey("accounts.account_id"), nullable=True
        ),
        sa.Column("metadata_value", sa.JSON(), nullable=False),
    )
    op.create_table(
        "wallet_signing_requests",
        sa.Column("signing_request_id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column(
            "account_id", sa.String(length=64), sa.ForeignKey("accounts.account_id"), nullable=False
        ),
        sa.Column("issuer_id", sa.String(length=66), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("signature", sa.String(length=132), nullable=True),
        sa.Column("verified_request_id", sa.String(length=128), nullable=True),
        sa.Column("verified_at", sa.BigInteger(), nullable=True),
        sa.Column("consumed_by", sa.String(length=66), nullable=True),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint("account_id", "kind", "request_id"),
    )
    op.create_table(
        "wallet_proposals",
        sa.Column("proposal_id", sa.String(length=66), primary_key=True, nullable=False),
        sa.Column(
            "account_id", sa.String(length=64), sa.ForeignKey("accounts.account_id"), nullable=False
        ),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("domain", sa.JSON(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.UniqueConstraint("account_id", "request_id"),
    )
    op.create_table(
        "wallet_document_versions",
        sa.Column("chain_id", sa.String(length=78), primary_key=True, nullable=False),
        sa.Column("verifying_contract", sa.String(length=42), primary_key=True, nullable=False),
        sa.Column("document_id", sa.String(length=66), primary_key=True, nullable=False),
        sa.Column("version", sa.BigInteger(), primary_key=True, nullable=False),
        sa.Column(
            "signing_request_id",
            sa.String(length=64),
            sa.ForeignKey("wallet_signing_requests.signing_request_id"),
            nullable=False,
        ),
        sa.Column("issuer_id", sa.String(length=66), nullable=False),
        sa.Column("message", sa.JSON(), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("original", sa.LargeBinary(), nullable=True),
        sa.Column("signature", sa.String(length=132), nullable=True),
        sa.Column("retain_until", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint("signing_request_id"),
    )
    op.create_table(
        "wallet_inputs",
        sa.Column("input_id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column(
            "account_id", sa.String(length=64), sa.ForeignKey("accounts.account_id"), nullable=False
        ),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("original", sa.LargeBinary(), nullable=True),
        sa.Column("accepted_at", sa.BigInteger(), nullable=False),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_wallet_inputs_account_id", "wallet_inputs", ["account_id"])
    op.create_table(
        "wallet_analyses",
        sa.Column("analysis_id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column(
            "account_id", sa.String(length=64), sa.ForeignKey("accounts.account_id"), nullable=False
        ),
        sa.Column(
            "input_id",
            sa.String(length=64),
            sa.ForeignKey("wallet_inputs.input_id"),
            nullable=False,
        ),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("accepted_at", sa.BigInteger(), nullable=False),
        sa.Column("started_at", sa.BigInteger(), nullable=True),
        sa.Column("completed_at", sa.BigInteger(), nullable=True),
        sa.Column("retain_report", sa.Boolean(), nullable=False),
        sa.Column("retain_original", sa.Boolean(), nullable=False),
        sa.Column("report_expires_at", sa.BigInteger(), nullable=True),
        sa.Column("original_expires_at", sa.BigInteger(), nullable=True),
        sa.Column("report", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.UniqueConstraint("input_id"),
        sa.UniqueConstraint("account_id", "request_id"),
    )
    op.create_index("ix_wallet_analyses_account_id", "wallet_analyses", ["account_id"])


def downgrade():
    op.drop_table("wallet_analyses")
    op.drop_table("wallet_inputs")
    op.drop_table("wallet_document_versions")
    op.drop_table("wallet_proposals")
    op.drop_table("wallet_signing_requests")
    op.drop_table("wallet_onboarding")
