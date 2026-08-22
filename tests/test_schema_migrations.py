from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from backend.services.schema_migrations import upgrade_schema


ROOT = Path(__file__).resolve().parent.parent


def test_upgrade_schema_creates_clean_database(tmp_path):
    engine, database_url = _engine(tmp_path, "clean.db")

    action = upgrade_schema(engine, database_url)

    assert action == "created"
    assert {"document_versions", "chunks", "alembic_version"}.issubset(
        inspect(engine).get_table_names()
    )
    engine.dispose()


def test_upgrade_schema_adopts_legacy_core_database(tmp_path):
    engine, database_url = _engine(tmp_path, "legacy.db")
    config = _config(database_url)
    command.upgrade(config, "0001_core_schema")
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE alembic_version"))

    action = upgrade_schema(engine, database_url)

    assert action == "adopted_core"
    assert {"document_versions", "chunks", "alembic_version"}.issubset(
        inspect(engine).get_table_names()
    )
    engine.dispose()


def test_upgrade_schema_rejects_partial_legacy_database(tmp_path):
    engine, database_url = _engine(tmp_path, "partial.db")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (user_id TEXT PRIMARY KEY)"))

    with pytest.raises(RuntimeError, match="partial legacy schema"):
        upgrade_schema(engine, database_url)
    engine.dispose()


def test_upgrade_schema_adopts_version_schema_at_its_actual_revision(tmp_path):
    engine, database_url = _engine(tmp_path, "legacy-versions.db")
    config = _config(database_url)
    command.upgrade(config, "0002_document_versions_chunks")
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE alembic_version"))

    action = upgrade_schema(engine, database_url)

    assert action == "adopted_versions"
    assert {"auth_sessions", "query_execution_traces", "claim_conflicts"}.issubset(
        inspect(engine).get_table_names()
    )
    engine.dispose()


def _engine(tmp_path, filename):
    database_url = f"sqlite:///{(tmp_path / filename).as_posix()}"
    return create_engine(database_url), database_url


def _config(database_url):
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config