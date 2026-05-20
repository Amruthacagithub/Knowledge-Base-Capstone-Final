import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "documents" / "manifest.json"


def test_manifest_paths_exist():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for entry in manifest:
        path = ROOT / "documents" / entry["path"]
        assert path.exists(), entry["path"]


def test_manifest_has_no_duplicate_paths():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    paths = [entry["path"] for entry in manifest]
    assert len(paths) == len(set(paths))


def test_manifest_includes_expanded_corpus_docs():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    paths = {entry["path"] for entry in manifest}
    assert "engineering/integration_map.md" in paths
    assert "engineering/internal_api_keys.md" in paths
    assert "hr/remote_work_policy_v2.md" in paths
    assert len([p for p in paths if p.endswith(".md")]) >= 48
