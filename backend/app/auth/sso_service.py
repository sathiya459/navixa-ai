from sqlalchemy.orm import Session

from app.models.role import VIEWER, Role, UserRole
from app.models.user import User


def get_or_create_entra_user(db: Session, claims: dict) -> User:
    """Finds or provisions a User row for a successful Entra ID login.

    New SSO users default to the Viewer role (least privilege) since there
    is no admin role-assignment endpoint yet - an Admin must promote them
    via direct DB access or a future role-management API. This is a known
    gap, not an oversight: building that endpoint is out of Phase 5 scope
    as originally defined (Section 20 doesn't call for it explicitly).
    """
    external_id = claims.get("oid") or claims.get("sub")
    email = claims.get("preferred_username") or claims.get("email")
    full_name = claims.get("name")

    user = db.query(User).filter(User.external_id == external_id, User.auth_provider == "entra_id").first()
    if user is not None:
        return user

    user = User(
        email=email,
        full_name=full_name,
        auth_provider="entra_id",
        external_id=external_id,
        hashed_password=None,
        is_active=True,
    )
    db.add(user)
    db.flush()

    viewer_role = db.query(Role).filter(Role.name == VIEWER).first()
    if viewer_role is not None:
        db.add(UserRole(user_id=user.id, role_id=viewer_role.id))

    db.commit()
    db.refresh(user)
    return user
