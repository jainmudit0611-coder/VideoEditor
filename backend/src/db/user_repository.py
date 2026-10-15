import uuid
import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from backend.src.db.models import User, UserRole

logger = logging.getLogger("brand-guardian-user-repository")

class UserRepository:
    """
    Data access repository for User entities.
    Handles normalized email lookups, creation, and profile retrieval.
    """

    @staticmethod
    def create_user(
        session: Session,
        email: str,
        password_hash: str,
        display_name: str,
        role: UserRole = UserRole.USER,
        is_active: bool = True,
        user_id: Optional[str] = None
    ) -> User:
        """Creates and persists a new User entity with a normalized email."""
        norm_email = email.strip().lower()
        uid = user_id or str(uuid.uuid4())
        user = User(
            id=uid,
            email=norm_email,
            password_hash=password_hash,
            display_name=display_name.strip(),
            role=role,
            is_active=is_active
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        logger.info(f"Created new user record: id={uid}, email={norm_email}, role={role.value}")
        return user

    @staticmethod
    def get_by_id(session: Session, user_id: str) -> Optional[User]:
        """Retrieves a User by primary key UUID."""
        if not user_id:
            return None
        return session.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_by_email(session: Session, email: str) -> Optional[User]:
        """Retrieves a User by normalized email address."""
        if not email:
            return None
        norm_email = email.strip().lower()
        return session.query(User).filter(User.email == norm_email).first()

    @staticmethod
    def list_users(session: Session, limit: int = 50, offset: int = 0) -> List[User]:
        """Lists users with pagination."""
        return (
            session.query(User)
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
