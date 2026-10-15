import logging
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.src.db.models import User, UserRole
from backend.src.db.user_repository import UserRepository
from backend.src.security.passwords import hash_password, verify_password
from backend.src.security.tokens import create_access_token
from backend.src.api.auth_schemas import UserRegisterRequest

logger = logging.getLogger("brand-guardian-auth-service")

class AuthService:
    """
    Service handling user registration, authentication credential validation,
    and JWT token issuance.
    """

    @staticmethod
    def register_user(session: Session, request: UserRegisterRequest, role: UserRole = UserRole.USER) -> User:
        """
        Registers a new user after verifying email uniqueness and hashing the password.
        Raises 409 Conflict if email already exists.
        """
        existing = UserRepository.get_by_email(session, request.email)
        if existing:
            logger.warning(f"Registration failed: Email '{request.email}' is already registered.")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email address already exists."
            )

        hashed = hash_password(request.password)
        user = UserRepository.create_user(
            session=session,
            email=request.email,
            password_hash=hashed,
            display_name=request.display_name,
            role=role,
            is_active=True
        )
        return user

    @staticmethod
    def authenticate_user(session: Session, email: str, password: str) -> Optional[User]:
        """
        Validates credentials without leaking whether email exists.
        Returns User on success, or None on failure.
        """
        user = UserRepository.get_by_email(session, email)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    @staticmethod
    def create_token_for_user(user: User) -> str:
        """Generates a signed JWT bearer token containing the user identity and role."""
        role_str = user.role.value if isinstance(user.role, UserRole) else str(user.role)
        payload = {
            "sub": user.id,
            "email": user.email,
            "role": role_str
        }
        return create_access_token(payload)
