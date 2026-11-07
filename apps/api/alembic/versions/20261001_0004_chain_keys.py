"""Durable chain recovery and protected issuer key references."""

import sqlalchemy as sa
from alembic import op

revision = "20261001_0004"
down_revision = "20260930_0003"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("issuer_applications", "operations", "audit_events"):
        op.execute(sa.text(f"UPDATE {table} SET created_at = now() WHERE created_at IS NULL"))
        op.alter_column(
            table, "created_at", existing_type=sa.DateTime(timezone=True), nullable=False
        )
    op.add_column("audit_events", sa.Column("reason", sa.String(500)))
    for name, datatype in (
        ("target_id", sa.String(128)),
        ("input_body", sa.JSON()),
        ("recovery_reference", sa.JSON()),
        ("chain_evidence", sa.JSON()),
        ("deployment_id", sa.String(68)),
    ):
        op.add_column("operations", sa.Column(name, datatype))
    op.create_table(
        "issuer_keys",
        sa.Column("key_id", sa.String(128), primary_key=True),
        sa.Column("issuer_id", sa.String(128), nullable=False, index=True),
        sa.Column("signer", sa.String(42), nullable=False),
        sa.Column("valid_from", sa.BigInteger(), nullable=False),
        sa.Column("valid_until", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("selected", sa.Boolean(), nullable=False),
        sa.Column("secret_ref", sa.String(128), nullable=False),
        sa.Column("deployment_id", sa.String(68), nullable=False),
    )


def downgrade():
    for table in ("issuer_applications", "operations", "audit_events"):
        op.alter_column(
            table, "created_at", existing_type=sa.DateTime(timezone=True), nullable=True
        )
    op.drop_column("audit_events", "reason")
    op.drop_table("issuer_keys")
    for name in (
        "deployment_id",
        "chain_evidence",
        "recovery_reference",
        "input_body",
        "target_id",
    ):
        op.drop_column("operations", name)
