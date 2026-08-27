"""Evaluate role-isolated document access without requiring Qdrant."""
import json
import os
import sys
import tempfile
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEST_ROOT = Path(tempfile.mkdtemp(prefix="role-compare-"))
shutil.copytree(ROOT / "documents", TEST_ROOT / "documents")
os.environ["DATABASE_URL"] = f"sqlite:///{(TEST_ROOT / 'role.db').as_posix()}"
os.environ["DOCUMENTS_DIR"] = str(TEST_ROOT / "documents")
os.environ["BM25_INDEX_DIR"] = str(TEST_ROOT / "indexdir")
os.environ["JWT_SECRET"] = "role-comparison-evaluation-only-32"
os.environ["AUTH_MODE"] = "demo"
os.environ["QDRANT_URL"] = " "
os.environ["QDRANT_API_KEY"] = " "
os.environ["GEMINI_API_KEY"] = ""
os.environ["MODEL_DEVICE"] = "cpu"
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from backend.database import Base, engine
from backend.main import app
from tests.conftest import _seed_test_database


ROLE_CHECKS = [
    {
        "role": "engineer",
        "email": "harshini@company.com",
        "forbidden_titles": ["compensation", "sales playbook", "quota"],
        "required_titles": ["internal api keys", "leave policy"],
    },
    {
        "role": "sales",
        "email": "tanvi@company.com",
        "forbidden_titles": ["internal api keys", "compensation"],
        "required_titles": ["pricing tiers"],
    },
    {
        "role": "employee",
        "email": "arijith@company.com",
        "forbidden_titles": ["compensation", "sales playbook", "internal api keys"],
        "required_titles": ["employee handbook"],
    },
    {
        "role": "admin",
        "email": "bhaskar@company.com",
        "forbidden_titles": [],
        "required_titles": ["compensation"],
    },
]


def evaluate() -> dict:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    _seed_test_database()
    client = TestClient(app)
    failures = []
    checks = 0

    for item in ROLE_CHECKS:
        login = client.post("/api/auth/login", json={"email": item["email"]})
        token = login.json()["token"]
        response = client.get(
            "/api/documents",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        titles = [doc["title"].lower() for doc in response.json().get("documents", [])]
        checks += 1
        for forbidden in item["forbidden_titles"]:
            if any(forbidden in title for title in titles):
                failures.append(
                    {
                        "role": item["role"],
                        "forbidden": forbidden,
                        "titles": titles,
                    }
                )
        if item["required_titles"]:
            checks += 1
            if not any(
                any(required in title for title in titles)
                for required in item["required_titles"]
            ):
                failures.append(
                    {
                        "role": item["role"],
                        "missing_required": item["required_titles"],
                    }
                )

    shutil.rmtree(TEST_ROOT, ignore_errors=True)
    return {
        "checks": checks,
        "failures": failures,
        "leakage_count": len(failures),
    }


def main() -> int:
    result = evaluate()
    print(json.dumps(result, indent=2))
    passed = result["leakage_count"] == 0
    print("PASS: role comparison evaluator passed." if passed else "FAIL: role comparison evaluator failed.")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
