"""Pytest fixtures."""
import json
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

INTEGRATION_MODE = os.getenv("TRUST_RAG_INTEGRATION") == "1"
TEST_ROOT = Path(tempfile.mkdtemp(prefix="trust-rag-tests-"))
if INTEGRATION_MODE:
    TEST_DOCUMENTS_DIR = ROOT / "documents"
    if not os.getenv("DATABASE_URL") or not os.getenv("JWT_SECRET"):
        raise RuntimeError(
            "Integration tests require explicit DATABASE_URL and JWT_SECRET"
        )
else:
    TEST_DOCUMENTS_DIR = TEST_ROOT / "documents"
    shutil.copytree(ROOT / "documents", TEST_DOCUMENTS_DIR)
    os.environ["DATABASE_URL"] = f"sqlite:///{(TEST_ROOT / 'test.db').as_posix()}"
    os.environ["DOCUMENTS_DIR"] = str(TEST_DOCUMENTS_DIR)
    os.environ["BM25_INDEX_DIR"] = str(TEST_ROOT / "indexdir")
    os.environ["JWT_SECRET"] = "trust-rag-test-secret"
    os.environ["AUTH_MODE"] = "demo"
    os.environ["QDRANT_URL"] = " "
    os.environ["QDRANT_API_KEY"] = " "
    os.environ["GEMINI_API_KEY"] = ""
    os.environ["GEMINI_API_KEY_2"] = ""
    os.environ["GEMINI_API_KEY_3"] = ""
    os.environ["EVIDENCE_EXTRACTION_ENABLED"] = "false"
    os.environ["EVIDENCE_GRAPH_ENABLED"] = "false"
    os.environ["TEMPORAL_API_ENABLED"] = "false"
    os.environ["CLAIM_VERIFICATION_ENABLED"] = "false"

os.environ.setdefault("MODEL_DEVICE", "cpu")

from backend.main import app
from backend.database import Base, SessionLocal, engine
from backend.models import Document, Role, User
from backend.services.auth import create_token


@pytest.fixture(scope="session", autouse=True)
def isolated_test_environment():
    if not INTEGRATION_MODE:
        Base.metadata.create_all(bind=engine)
        _seed_test_database()
    yield
    engine.dispose()
    shutil.rmtree(TEST_ROOT, ignore_errors=True)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def admin_token():
    return create_token("bhaskar")


@pytest.fixture
def engineer_token():
    return create_token("harshini")


@pytest.fixture
def hr_token():
    return create_token("amrutha")


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def engineer_headers(engineer_token):
    return {"Authorization": f"Bearer {engineer_token}"}


@pytest.fixture
def hr_headers(hr_token):
    return {"Authorization": f"Bearer {hr_token}"}


@pytest.fixture
def sample_md(tmp_path):
    p = tmp_path / "sample.md"
    p.write_text("# Title\n\nHello world policy text.\n", encoding="utf-8")
    return p


@pytest.fixture
def sample_pdf(tmp_path):
    try:
        from fpdf import FPDF
    except ImportError:
        pytest.skip("fpdf2 not installed")
    p = tmp_path / "sample.pdf"
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 8, "Page one content about PTO policy.")
    pdf.add_page()
    pdf.multi_cell(0, 8, "Page two content about remote work.")
    pdf.output(str(p))
    return p


def _seed_test_database():
    role_names = ["Employee", "HR", "Engineer", "Sales", "Admin"]
    users = [
        ("amrutha", "amrutha@company.com", "HR", ["Employee", "HR"]),
        ("harshini", "harshini@company.com", "Engineering", ["Employee", "Engineer"]),
        ("tanvi", "tanvi@company.com", "Sales", ["Employee", "Sales"]),
        ("bhaskar", "bhaskar@company.com", "Engineering", ["Employee", "Admin"]),
        ("arijith", "arijith@company.com", "HR", ["Employee"]),
    ]

    db = SessionLocal()
    try:
        roles = {name: Role(role_name=name) for name in role_names}
        db.add_all(roles.values())
        db.flush()

        for user_id, email, department, user_role_names in users:
            user = User(user_id=user_id, email=email, department=department)
            user.roles = [roles[name] for name in user_role_names]
            db.add(user)

        manifest = json.loads(
            (TEST_DOCUMENTS_DIR / "manifest.json").read_text(encoding="utf-8")
        )
        for entry in manifest:
            db.add(
                Document(
                    id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"trust-rag:{entry['path']}")),
                    title=entry["title"],
                    department=entry["department"],
                    classification=entry["classification"],
                    file_path=entry["path"],
                )
            )
        db.commit()
    finally:
        db.close()
