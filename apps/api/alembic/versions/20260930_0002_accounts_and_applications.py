"""Add prepared accounts, sessions, applications, and audit events.

Revision ID: 20260930_0002
Revises: 20260906_0001
"""

import sqlalchemy as sa
from alembic import op

revision = "20260930_0002"
down_revision = "20260906_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("account_id", sa.String(64), primary_key=True),
        sa.Column("username", sa.String(120), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("issuer_id", sa.String(128)),
    )
    op.create_table(
        "account_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column(
            "account_id", sa.String(64), sa.ForeignKey("accounts.account_id"), nullable=False
        ),
        sa.Column("csrf_token", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "issuer_applications",
        sa.Column("application_id", sa.String(64), primary_key=True),
        sa.Column("issuer_id", sa.String(128), nullable=False, unique=True),
        sa.Column(
            "applicant_account_id",
            sa.String(64),
            sa.ForeignKey("accounts.account_id"),
            nullable=False,
        ),
        sa.Column("issuer_name", sa.String(120), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("decision_reason", sa.String(500)),
        sa.Column("decided_by_account_id", sa.String(64), sa.ForeignKey("accounts.account_id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "audit_events",
        sa.Column("event_id", sa.String(64), primary_key=True),
        sa.Column(
            "actor_account_id", sa.String(64), sa.ForeignKey("accounts.account_id"), nullable=False
        ),
        sa.Column("issuer_id", sa.String(128)),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("target_id", sa.String(128), nullable=False),
        sa.Column("before_status", sa.String(32)),
        sa.Column("after_status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    for table in (
        "audit_events",
        "issuer_applications",
        "account_sessions",
        "accounts",
    ):
        op.drop_table(table)
