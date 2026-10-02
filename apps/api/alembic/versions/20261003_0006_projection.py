"""C lifecycle for B projection tables; preserve all API data on rollback."""

from alembic import op
from originproof_indexer.projection import metadata

revision = "20261003_0006"
down_revision = "20261001_0005"
branch_labels = None
depends_on = None


def upgrade():
    metadata.create_all(op.get_bind())


def downgrade():
    metadata.drop_all(op.get_bind())
