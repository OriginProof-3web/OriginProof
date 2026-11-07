"""C lifecycle for B projection tables; preserve all API data on rollback."""

from alembic import op
from sqlalchemy import BigInteger, Column, MetaData, String, Table

revision = "20261003_0006"
down_revision = "20261001_0005"
branch_labels = None
depends_on = None


# Freeze this revision: later indexer model changes need a new migration.
metadata = MetaData()
events = Table(
    "chain_events",
    metadata,
    Column("chain_id", BigInteger, primary_key=True),
    Column("deployment_id", String(68), primary_key=True),
    Column("block_number", BigInteger, primary_key=True),
    Column("log_index", BigInteger, primary_key=True),
    Column("block_hash", String(66), nullable=False),
    Column("transaction_hash", String(66), nullable=False),
)
checkpoints = Table(
    "chain_checkpoints",
    metadata,
    Column("chain_id", BigInteger, primary_key=True),
    Column("deployment_id", String(68), primary_key=True),
    Column("block_number", BigInteger, nullable=False),
    Column("block_hash", String(66), nullable=False),
)
processed_blocks = Table(
    "chain_processed_blocks",
    metadata,
    Column("chain_id", BigInteger, primary_key=True),
    Column("deployment_id", String(68), primary_key=True),
    Column("block_number", BigInteger, primary_key=True),
    Column("block_hash", String(66), nullable=False),
)
proof_events = Table(
    "proof_chain_events",
    metadata,
    Column("chain_id", BigInteger, primary_key=True),
    Column("deployment_id", String(68), primary_key=True),
    Column("block_number", BigInteger, primary_key=True),
    Column("log_index", BigInteger, primary_key=True),
    Column("proof_id_hash", String(66), nullable=False),
    Column("event_type", String(16), nullable=False),
)


def upgrade():
    metadata.create_all(op.get_bind())


def downgrade():
    metadata.drop_all(op.get_bind())
