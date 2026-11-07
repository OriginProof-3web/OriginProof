"""Personal sign-up keeps a member ID as username; the synthetic mail moves to its own column."""

import sqlalchemy as sa
from alembic import op

revision = "20261104_0010"
down_revision = "20261016_0009"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("accounts", sa.Column("email", sa.String(120), nullable=True))
    op.create_unique_constraint("uq_accounts_email", "accounts", ["email"])


def downgrade():
    op.drop_constraint("uq_accounts_email", "accounts", type_="unique")
    op.drop_column("accounts", "email")
