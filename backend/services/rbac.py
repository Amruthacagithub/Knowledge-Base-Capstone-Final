"""Shared RBAC helpers with no ML or vector-store dependencies."""


def department_to_role(department: str) -> str:
    """Map department name to role name."""
    mapping = {
        "HR": "HR",
        "Engineering": "Engineer",
        "Sales": "Sales",
    }
    return mapping.get(department, "Employee")
