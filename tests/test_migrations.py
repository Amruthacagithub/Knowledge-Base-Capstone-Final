from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


ROOT = Path(__file__).resolve().parent.parent


def test_migrations_upgrade_and_downgrade_clean_database(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'migrations.db').as_posix()}"
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    tables = set(inspect(engine).get_table_names())
    assert tables == {
        "users",
        "roles",
        "user_roles",
        "documents",
        "access_audit_log",
        "auth_sessions",
        "document_versions",
        "chunks",
        "ingest_jobs",
        "extraction_runs",
        "entities",
        "entity_mentions",
        "evidence_claims",
        "evidence_relationships",
        "retrieval_traces",
        "query_execution_traces",
        "claim_conflicts",
        "alembic_version",
    }

    version_columns = {
        column["name"] for column in inspect(engine).get_columns("document_versions")
    }
    assert version_columns.issuperset(
        {"content_hash", "effective_from", "effective_to", "is_current"}
    )
    document_columns = {
        column["name"] for column in inspect(engine).get_columns("documents")
    }
    assert document_columns.issuperset({"source_kind", "is_active", "deprecated_at"})
    user_columns = {column["name"] for column in inspect(engine).get_columns("users")}
    assert user_columns.issuperset({"password_hash", "is_active"})

    command.check(config)

    command.downgrade(config, "base")

    assert inspect(engine).get_table_names() == ["alembic_version"]
    engine.dispose()