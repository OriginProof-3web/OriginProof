"""create signed proof storage

Revision ID: 20260906_0001
Revises:
Create Date: 2026-09-06
"""

import sqlalchemy as sa
from alembic import op

revision = "20260906_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "signed_proofs",
        sa.Column("proof_id", sa.String(length=128), nullable=False),
        sa.Column("issuer_id", sa.String(length=128), nullable=False),
        sa.Column("key_id", sa.String(length=128), nullable=False),
        sa.Column("payload_hash", sa.String(length=66), nullable=False),
        sa.Column("envelope", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("proof_id"),
    )
    op.create_index("ix_signed_proofs_issuer_id", "signed_proofs", ["issuer_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_signed_proofs_issuer_id", table_name="signed_proofs")
    op.drop_table("signed_proofs")
