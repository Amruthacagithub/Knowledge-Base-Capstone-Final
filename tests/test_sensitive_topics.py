from backend.services.auth import UserContext
from backend.services.sensitive_topics import (
    blocks_sensitive_search,
    is_hr_compensation_query,
    is_sales_compensation_query,
)


def _user(*roles: str) -> UserContext:
    return UserContext(
        user_id="test",
        email="test@company.com",
        department="Engineering",
        roles=list(roles),
    )


def test_executive_salary_query_is_compensation():
    assert is_hr_compensation_query("What are the executive salary bands?")


def test_pto_query_is_not_compensation():
    assert not is_hr_compensation_query("What is the PTO policy?")


def test_engineer_blocked_from_salary_search():
    engineer = _user("Employee", "Engineer")
    assert blocks_sensitive_search(engineer, "What are the executive salary bands?")


def test_hr_can_search_salary():
    hr = _user("Employee", "HR")
    assert not blocks_sensitive_search(hr, "What are the salary bands?")


def test_admin_can_search_salary():
    admin = _user("Employee", "Admin")
    assert not blocks_sensitive_search(admin, "What are the salary bands?")


def test_engineer_blocked_from_sales_commission():
    engineer = _user("Employee", "Engineer")
    assert is_sales_compensation_query("What is the sales commission structure?")
    assert blocks_sensitive_search(engineer, "What is the sales commission structure?")


def test_sales_can_search_commission():
    sales = _user("Employee", "Sales")
    assert not blocks_sensitive_search(sales, "What is the sales commission structure?")
