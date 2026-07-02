import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.entra import acquire_token_by_authorization_code, get_authorization_url, is_entra_configured
from app.auth.security import create_token, decode_token, verify_password
from app.auth.sso_service import get_or_create_entra_user
from app.config.settings import get_settings
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Auth"])
settings = get_settings()


def _issue_tokens(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_token(user.id, "access"),
        refresh_token=create_token(user.id, "refresh"),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if (
        user is None
        or user.hashed_password is None
        or not verify_password(payload.password, user.hashed_password)
        or not user.is_active
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    return _issue_tokens(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    token_payload = decode_token(payload.refresh_token)
    if token_payload is None or token_payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    user = db.get(User, uuid.UUID(token_payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    return _issue_tokens(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(current_user: User = Depends(get_current_user)) -> None:
    # Stateless JWT: client discards tokens. Token blacklist/rotation can be
    # added later (e.g. via navixa_cache) if immediate revocation is required.
    return None


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        roles=current_user.role_names,
    )


@router.get("/sso/entra/login")
def entra_login() -> RedirectResponse:
    """Redirects to Microsoft's authorize endpoint. MFA, if required, is
    enforced by the tenant's Entra Conditional Access policy at this step -
    not by this application."""
    if not is_entra_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Entra ID SSO is not configured on this deployment",
        )
    state = secrets.token_urlsafe(24)
    return RedirectResponse(get_authorization_url(state))


@router.get("/sso/entra/callback")
def entra_callback(code: str, db: Session = Depends(get_db)) -> RedirectResponse:
    """Redirects back into the SPA with tokens in the URL fragment (never a
    query string, so they aren't captured in server access logs or
    Referer headers) rather than returning JSON directly - the browser
    navigated here via a full-page redirect from Entra, so JSON in the
    response would just be displayed raw instead of landing the user back
    in the app. On failure, redirects with an `error` fragment instead of
    raising, since there's no SPA route mounted to render an HTTPException.
    """
    if not is_entra_configured():
        return RedirectResponse(f"{settings.frontend_sso_redirect_url}#error=sso_not_configured")

    token_result = acquire_token_by_authorization_code(code)
    claims = token_result.get("id_token_claims")
    if claims is None:
        error = token_result.get("error_description", "sso_failed")
        return RedirectResponse(f"{settings.frontend_sso_redirect_url}#error={error}")

    user = get_or_create_entra_user(db, claims)
    if not user.is_active:
        return RedirectResponse(f"{settings.frontend_sso_redirect_url}#error=account_disabled")

    tokens = _issue_tokens(user)
    return RedirectResponse(
        f"{settings.frontend_sso_redirect_url}"
        f"#access_token={tokens.access_token}&refresh_token={tokens.refresh_token}"
    )
