"""
Initialize the database: create all tables and seed demo users + roles.
Run: python scripts/init_db.py
"""
import sys
from pathlib import Path

# Add project root to path so we can import backend modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import AUTH_MODE, BOOTSTRAP_USER_PASSWORD, DATABASE_URL
from backend.database import engine, SessionLocal
from backend.models import User, Role
from backend.services.auth import hash_password
from backend.services.schema_migrations import upgrade_schema


DEMO_USERS = [
    {"user_id": "amrutha", "email": "amrutha@company.com", "department": "HR", "roles": ["Employee", "HR"]},
    {"user_id": "harshini", "email": "harshini@company.com", "department": "Engineering", "roles": ["Employee", "Engineer"]},
    {"user_id": "tanvi", "email": "tanvi@company.com", "department": "Sales", "roles": ["Employee", "Sales"]},
    {"user_id": "bhaskar", "email": "bhaskar@company.com", "department": "Engineering", "roles": ["Employee", "Admin"]},
    {"user_id": "arijith", "email": "arijith@company.com", "department": "HR", "roles": ["Employee"]},
]


def init_db():
    """Create or migrate all tables."""
    action = upgrade_schema(engine, DATABASE_URL)
    print(f"✓ Database schema ready ({action}).")


def seed_roles(db):
    """Seed the 5 roles."""
    role_names = ["Employee", "HR", "Engineer", "Sales", "Admin"]
    created = 0
    for name in role_names:
        existing = db.query(Role).filter(Role.role_name == name).first()
        if not existing:
            db.add(Role(role_name=name))
            created += 1
    db.commit()
    print(f"✓ {created} roles seeded ({len(role_names) - created} already existed).")


def seed_users(db):
    """Seed 5 demo users with their roles."""
    if (
        AUTH_MODE == "password"
        and not BOOTSTRAP_USER_PASSWORD
        and _users_need_password(db)
    ):
        raise RuntimeError(
            "BOOTSTRAP_USER_PASSWORD is required to seed password-mode users"
        )
    encoded_password = (
        hash_password(BOOTSTRAP_USER_PASSWORD)
        if BOOTSTRAP_USER_PASSWORD
        else None
    )
    created = sum(
        _seed_user(db, user_data, encoded_password)
        for user_data in DEMO_USERS
    )
    db.commit()
    print(f"✓ {created} users seeded ({len(DEMO_USERS) - created} already existed).")


def _users_need_password(db) -> bool:
    return any(
        (existing := db.get(User, user_data["user_id"])) is None
        or not existing.password_hash
        for user_data in DEMO_USERS
    )


def _seed_user(db, user_data: dict, encoded_password: str | None) -> int:
    existing = db.get(User, user_data["user_id"])
    if existing is not None:
        if not existing.password_hash and encoded_password:
            existing.password_hash = encoded_password
        return 0
    user = User(
        user_id=user_data["user_id"],
        email=user_data["email"],
        department=user_data["department"],
        password_hash=encoded_password,
    )
    roles = (
        db.query(Role)
        .filter(Role.role_name.in_(user_data["roles"]))
        .all()
    )
    user.roles.extend(roles)
    db.add(user)
    return 1


def main():
    print("=== Knowledge Base — Database Initialization ===\n")
    init_db()

    db = SessionLocal()
    try:
        seed_roles(db)
        seed_users(db)
    finally:
        db.close()

    print("\n=== Done! Database is ready. ===")


if __name__ == "__main__":
    main()
