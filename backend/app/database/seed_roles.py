"""One-off script to seed the default RBAC roles (admin, auditor, viewer).

Usage: python -m app.database.seed_roles
"""

from app.database.session import SessionLocal
from app.models.role import DEFAULT_ROLES, Role


def seed_roles() -> None:
    db = SessionLocal()
    try:
        for name in DEFAULT_ROLES:
            if not db.query(Role).filter(Role.name == name).first():
                db.add(Role(name=name))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed_roles()
