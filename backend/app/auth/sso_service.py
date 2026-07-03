from sqlalchemy.orm import Session

from app.models.role import READER, Role, UserRole
from app.models.user import User


def get_or_create_entra_user(db: Session, claims: dict) -> User:
    """Finds or provisions a User row for a successful Entra ID login.

    Every SSO login defaults to the Reader role (least privilege) - Admin
    is reserved for the local `admin@navixa.ai` account only. There is no
    admin role-assignment endpoint yet - an Admin must promote an SSO user
    to Admin via direct DB access or a future role-management API. This is
    a known gap, not an oversight.
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

    reader_role = db.query(Role).filter(Role.name == READER).first()
    if reader_role is not None:
        db.add(UserRole(user_id=user.id, role_id=reader_role.id))

    db.commit()
    db.refresh(user)
    return user
