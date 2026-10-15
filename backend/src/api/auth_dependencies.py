import logging
import jwt
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.src.db.database import get_db
from backend.src.db.models import User, UserRole
from backend.src.db.user_repository import UserRepository
from backend.src.security.tokens import decode_access_token

logger = logging.getLogger("brand-guardian-auth-dependencies")

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
    auto_error=False
)

def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency extracting and validating the JWT Bearer token.
    Raises 401 Unauthorized for missing, invalid, or expired tokens.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception

    try:
        payload = decode_access_token(token)
        user_id: Optional[str] = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        logger.info("Authentication failed: Token has expired.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError as e:
        logger.warning(f"Authentication failed: Invalid JWT token ({e})")
        raise credentials_exception

    user = UserRepository.get_by_id(db, user_id)
    if not user:
        logger.warning(f"Authentication failed: User id '{user_id}' not found in database.")
        raise credentials_exception

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    FastAPI dependency verifying the authenticated user is currently active.
    Raises 403 Forbidden if user is inactive.
    """
    if not current_user.is_active:
        logger.warning(f"Access denied: User '{current_user.email}' is inactive.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account."
        )
    return current_user


def require_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    FastAPI dependency ensuring the authenticated user has the ADMIN role.
    Raises 403 Forbidden for non-admin users.
    """
    user_role = current_user.role.value if isinstance(current_user.role, UserRole) else str(current_user.role)
    if user_role != UserRole.ADMIN.value:
        logger.warning(f"Access denied: User '{current_user.email}' lacks ADMIN privileges.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required."
        )
    return current_user
