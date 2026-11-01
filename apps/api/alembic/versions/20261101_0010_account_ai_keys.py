"""Member-owned AI keys; only AES-GCM ciphertext and the last four characters are stored."""

import sqlalchemy as sa
from alembic import op

revision = "20261101_0010"
down_revision = "20261016_0009"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "account_ai_keys",
        sa.Column(
            "account_id",
            sa.String(64),
            sa.ForeignKey("accounts.account_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("nonce", sa.LargeBinary(), nullable=False),
        sa.Column("ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("hint", sa.String(4), nullable=False),
        sa.Column("input_tokens", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("output_tokens", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("analyses", sa.BigInteger(), server_default="0", nullable=False),
    )


def downgrade():
    op.drop_table("account_ai_keys")
