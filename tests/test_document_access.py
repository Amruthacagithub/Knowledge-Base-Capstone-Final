from backend.models import Document
from backend.services.auth import get_user_context
from backend.services.document_access import user_can_access_document


def _doc(dept, classification):
    return Document(
        id="test-id",
        title="Test",
        department=dept,
        classification=classification,
        file_path="hr/x.md",
    )


def test_admin_sees_restricted():
    admin = get_user_context("bhaskar")
    assert user_can_access_document(_doc("HR", "restricted"), admin)


def test_engineer_blocked_hr_restricted():
    eng = get_user_context("harshini")
    assert not user_can_access_document(_doc("HR", "restricted"), eng)


def test_hr_sees_hr_restricted():
    hr = get_user_context("amrutha")
    assert user_can_access_document(_doc("HR", "restricted"), hr)


def test_public_any_employee():
    emp = get_user_context("arijith")
    assert user_can_access_document(_doc("HR", "public"), emp)
