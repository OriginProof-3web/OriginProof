"""Frozen 0006 DDL matches projection models and preserves existing data."""

import importlib.util
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from originproof_indexer.projection import metadata
from sqlalchemy import create_engine, inspect, text


def test_projection_revision_is_repeatable_and_preserves_api_data():
    path = (
        Path(__file__).resolve().parents[2]
        / "apps/api/alembic/versions/20261003_0006_projection.py"
    )
    spec = importlib.util.spec_from_file_location("projection_revision", path)
    revision = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(revision)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE legacy_api (id INTEGER PRIMARY KEY)"))
        connection.execute(text("INSERT INTO legacy_api VALUES (7)"))
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            revision.upgrade()
            connection.execute(
                text(
                    "INSERT INTO chain_checkpoints VALUES "
                    "(31337, 'synthetic-deployment', 1, '0x01')"
                )
            )
            revision.upgrade()
            assert connection.scalar(text("SELECT block_number FROM chain_checkpoints")) == 1
            assert (
                compare_metadata(
                    MigrationContext.configure(
                        connection,
                        opts={
                            "include_object": lambda obj, name, type_, reflected, compare_to: name
                            != "legacy_api"
                        },
                    ),
                    metadata,
                )
                == []
            )
            revision.downgrade()
            assert inspect(connection).get_table_names() == ["legacy_api"]
            assert connection.scalar(text("SELECT id FROM legacy_api")) == 7
            revision.upgrade()
            assert set(inspect(connection).get_table_names()) == {"legacy_api", *metadata.tables}
    engine.dispose()
