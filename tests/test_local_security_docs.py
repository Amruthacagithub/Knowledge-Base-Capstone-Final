from pathlib import Path

DOC = Path(__file__).resolve().parent.parent / "docs" / "LOCAL_SECURITY.md"
GITIGNORE = Path(__file__).resolve().parent.parent / ".gitignore"
ROOT = Path(__file__).resolve().parent.parent


def test_local_security_doc_has_required_sections():
    text = DOC.read_text(encoding="utf-8")
    setup = (ROOT / "docs" / "LOCAL_CPU_SETUP.md").read_text(encoding="utf-8")
    required = [
        "Authentication modes",
        "JWT_SECRET",
        "Rate limiting",
        "per-process",
        "Prompt-source quarantine",
        "9E",
        ".env",
    ]
    for section in required:
        assert section in text, f"missing section or keyword: {section}"
    assert "LOCAL_STACK" in setup


def test_gitignore_covers_secrets_and_caches():
    text = GITIGNORE.read_text(encoding="utf-8")
    for pattern in (".env", "indexdir/", ".cache/", "frontend/test-results/"):
        assert pattern in text, f".gitignore missing {pattern}"
