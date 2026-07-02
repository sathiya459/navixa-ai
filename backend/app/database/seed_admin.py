"""One-off script to create the first NAVIXA Admin user for local dev.

Usage: python -m app.database.seed_admin
Set NAVIXA_ADMIN_EMAIL / NAVIXA_ADMIN_PASSWORD to override the defaults.
"""

import os

from app.auth.security import hash_password
from app.database.session import SessionLocal
from app.models.role import ADMIN, Role, UserRole
from app.models.user import User

DEFAULT_EMAIL = "admin@navixa.ai"
DEFAULT_PASSWORD = "NavixaAdmin!2026"


def seed_admin() -> None:
    email = os.environ.get("NAVIXA_ADMIN_EMAIL", DEFAULT_EMAIL)
    password = os.environ.get("NAVIXA_ADMIN_PASSWORD", DEFAULT_PASSWORD)

    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            print(f"User {email} already exists.")
            return

        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name="NAVIXA Admin",
            auth_provider="local",
            is_active=True,
        )
        db.add(user)
        db.flush()

        admin_role = db.query(Role).filter(Role.name == ADMIN).first()
        if admin_role is None:
            raise RuntimeError("Admin role not found - run `python -m app.database.seed_roles` first")
        db.add(UserRole(user_id=user.id, role_id=admin_role.id))
        db.commit()
        print(f"Created admin user: {email} / {password}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin()
