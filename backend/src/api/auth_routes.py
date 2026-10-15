import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.src.db.database import get_db
from backend.src.db.models import User, UserRole
from backend.src.services.auth_service import AuthService
from backend.src.api.auth_schemas import (
    UserRegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
)
from backend.src.api.auth_dependencies import get_current_active_user

from backend.src.observability import log_event, ObservabilityEvent

logger = logging.getLogger("brand-guardian-auth-routes")

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    request: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Registers a new user account with hashed password.
    Returns safe user information excluding password credentials.
    """
    user = AuthService.register_user(db, request, role=UserRole.USER)
    log_event(logger, ObservabilityEvent.AUTH_REGISTRATION, message=f"User registered: user_id={user.id}", user_id=user.id)
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role.value if isinstance(user.role, UserRole) else str(user.role),
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else None
    )


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticates user credentials and issues a signed JWT Bearer access token.
    Uses generic error responses to prevent account enumeration.
    """
    user = AuthService.authenticate_user(db, request.email, request.password)
    if not user:
        log_event(logger, ObservabilityEvent.AUTH_LOGIN_FAILURE, level=logging.WARNING, message="Authentication failure for login attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        log_event(logger, ObservabilityEvent.AUTH_FORBIDDEN, level=logging.WARNING, message=f"Forbidden login for inactive user: user_id={user.id}", user_id=user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account."
        )

    access_token = AuthService.create_token_for_user(user)
    log_event(logger, ObservabilityEvent.AUTH_LOGIN_SUCCESS, message=f"User authenticated successfully: user_id={user.id}", user_id=user.id)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer"
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieves the authenticated user's profile.
    Strictly excludes password_hash and internal security parameters.
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        role=current_user.role.value if isinstance(current_user.role, UserRole) else str(current_user.role),
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat() if current_user.created_at else None
    )
