"""Evaluate graph path accuracy and authorization leakage on a fixed matrix."""
import hashlib
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "graph-evaluation-only-32-characters")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.database import Base
from backend.models import (
    Chunk,
    Document,
    DocumentVersion,
    Entity,
    EntityMention,
    EvidenceRelationship,
    ExtractionRun,
)
from backend.services.auth import UserContext
from backend.services.graph_traversal import GraphEntityUnavailable, traverse_visible_graph


ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = ROOT / "evaluation" / "graph_traversal_v1.json"


def evaluate(dataset_path: Path = DATASET_PATH) -> dict:
    dataset_bytes = dataset_path.read_bytes()
    cases = json.loads(dataset_bytes.decode("utf-8"))
    predicted_total = 0
    expected_total = 0
    true_positive = 0
    exact_cases = 0
    leakage_count = 0
    failures = []

    for case in cases:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            _seed_case(db, case)
            predicted_paths, error, truncated = _run_case(db, case)
        engine.dispose()

        expected_paths = {tuple(path) for path in case["expected_paths"]}
        predicted_total += len(predicted_paths)
        expected_total += len(expected_paths)
        true_positive += len(predicted_paths & expected_paths)
        leaked = {
            entity_id
            for path in predicted_paths
            for entity_id in path
            if entity_id in set(case["forbidden_entities"])
        }
        leakage_count += len(leaked)
        expected_error = case.get("expected_error")
        exact = (
            predicted_paths == expected_paths
            and error == expected_error
            and truncated == case["expected_truncated"]
            and not leaked
        )
        exact_cases += int(exact)
        if not exact:
            failures.append(
                {
                    "id": case["id"],
                    "missing_paths": sorted(expected_paths - predicted_paths),
                    "unexpected_paths": sorted(predicted_paths - expected_paths),
                    "expected_error": expected_error,
                    "actual_error": error,
                    "leaked_entities": sorted(leaked),
                    "expected_truncated": case["expected_truncated"],
                    "actual_truncated": truncated,
                }
            )

    precision = true_positive / predicted_total if predicted_total else 1.0
    recall = true_positive / expected_total if expected_total else 1.0
    path_f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "dataset": dataset_path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "cases": len(cases),
        "exact_case_accuracy": exact_cases / len(cases),
        "path_precision": precision,
        "path_recall": recall,
        "path_f1": path_f1,
        "forbidden_entity_leakage": leakage_count,
        "failures": failures,
    }


def _run_case(db, case):
    user_ctx = UserContext(
        user_id=f"eval-{case['id']}",
        email=f"{case['id']}@example.com",
        department="Engineering",
        roles=case["roles"],
    )
    try:
        result = traverse_visible_graph(
            db,
            user_ctx,
            case["start"],
            max_depth=case["max_depth"],
            max_paths=case["max_paths"],
        )
        return {path.entity_ids for path in result.paths}, None, result.truncated
    except GraphEntityUnavailable as exc:
        return set(), str(exc), False


def _seed_case(db, case):
    for edge in case["edges"]:
        prefix = f"{case['id']}-{edge['id']}"
        document = Document(
            id=f"{prefix}-document",
            title=prefix,
            department=edge["department"],
            classification=edge["classification"],
            file_path=f"evaluation/{prefix}.md",
            source_kind="manifest",
            is_active=edge.get("active", True),
        )
        version = DocumentVersion(
            id=f"{prefix}-version",
            document=document,
            version_number=1,
            content_hash=hashlib.sha256(prefix.encode()).hexdigest(),
            storage_uri=f"file:///tmp/{prefix}.md",
            file_type="markdown",
            file_size_bytes=20,
            is_current=edge.get("current", True),
        )
        chunk = Chunk(
            id=f"{prefix}-chunk",
            document_version=version,
            sequence_index=0,
            text_content=f"{edge['source']} {edge.get('relationship_type', 'depends_on')} {edge['target']}",
            content_hash=hashlib.sha256(f"{prefix}-chunk".encode()).hexdigest(),
            page_start=1,
            page_end=1,
        )
        run = ExtractionRun(
            id=f"{prefix}-run",
            document_version_id=version.id,
            extractor_name="evaluation",
            extractor_version="1",
            schema_version="1",
            status="succeeded",
        )
        source = _entity(db, edge["source"])
        target = _entity(db, edge["target"])
        db.add_all([document, version, chunk, run, source, target])
        db.flush()
        for index, entity in enumerate((source, target)):
            db.add(
                EntityMention(
                    id=f"{prefix}-mention-{index}",
                    entity_id=entity.id,
                    chunk_id=chunk.id,
                    extraction_run_id=run.id,
                    surface_text=entity.display_name,
                    start_char=index * 20,
                    end_char=index * 20 + len(entity.display_name),
                    confidence=1.0,
                )
            )
        db.add(
            EvidenceRelationship(
                id=f"{edge['id']}-relationship",
                chunk_id=chunk.id,
                extraction_run_id=run.id,
                source_entity_id=source.id,
                target_entity_id=target.id,
                relationship_type=edge.get("relationship_type", "depends_on"),
                evidence_text=chunk.text_content,
                confidence=1.0,
            )
        )
        db.flush()


def _entity(db, entity_id):
    return db.get(Entity, entity_id) or Entity(
        id=entity_id,
        entity_type="system",
        canonical_name=entity_id,
        display_name=entity_id,
    )


def main() -> int:
    result = evaluate()
    print(json.dumps(result, indent=2))
    passed = (
        result["exact_case_accuracy"] >= 0.95
        and result["path_f1"] >= 0.95
        and result["forbidden_entity_leakage"] == 0
    )
    print("PASS: graph traversal matrix passed." if passed else "FAIL: graph traversal matrix failed.")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())