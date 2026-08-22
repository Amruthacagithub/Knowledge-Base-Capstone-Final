"""Programmatic Alembic migration entry points for setup and deployment."""
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORE_TABLES = {
    "users",
    "roles",
    "user_roles",
    "documents",
    "access_audit_log",
}
VERSION_TABLES = {"document_versions", "chunks"}
CORE_REVISION = "0001_core_schema"
VERSION_REVISION = "0002_document_versions_chunks"
HEAD_TABLES = CORE_TABLES | VERSION_TABLES | {
    "ingest_jobs",
    "extraction_runs",
    "entities",
    "entity_mentions",
    "evidence_claims",
    "evidence_relationships",
    "retrieval_traces",
    "claim_conflicts",
    "query_execution_traces",
    "auth_sessions",
}
ADVANCED_TABLES = HEAD_TABLES - CORE_TABLES - VERSION_TABLES


def upgrade_schema(engine, database_url: str) -> str:
    """Upgrade a clean, Alembic-managed, or legacy core database to head."""
    tables = set(inspect(engine).get_table_names())
    config = _alembic_config(database_url)

    with engine.connect() as connection:
        config.attributes["connection"] = connection
        if "alembic_version" in tables:
            command.upgrade(config, "head")
            return "upgraded"

        if not tables:
            command.upgrade(config, "head")
            return "created"

        missing_core = CORE_TABLES - tables
        if missing_core:
            missing = ", ".join(sorted(missing_core))
            raise RuntimeError(f"Cannot adopt partial legacy schema; missing: {missing}")

        if HEAD_TABLES.issubset(tables):
            _validate_head_columns(engine)
            command.stamp(config, "head")
            return "adopted_head"

        if VERSION_TABLES.issubset(tables):
            unexpected = ADVANCED_TABLES & tables
            if unexpected:
                names = ", ".join(sorted(unexpected))
                raise RuntimeError(
                    "Cannot adopt ambiguous partial advanced schema; "
                    f"found: {names}"
                )
            command.stamp(config, VERSION_REVISION)
            command.upgrade(config, "head")
            return "adopted_versions"

        command.stamp(config, CORE_REVISION)
        command.upgrade(config, "head")
        return "adopted_core"


def _validate_head_columns(engine) -> None:
    inspector = inspect(engine)
    requirements = {
        "users": {"password_hash", "is_active"},
        "documents": {"source_kind", "is_active", "deprecated_at"},
    }
    for table, required in requirements.items():
        actual = {column["name"] for column in inspector.get_columns(table)}
        missing = required - actual
        if missing:
            names = ", ".join(sorted(missing))
            raise RuntimeError(
                f"Cannot adopt incomplete head schema; {table} missing: {names}"
            )


def _alembic_config(database_url: str) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config