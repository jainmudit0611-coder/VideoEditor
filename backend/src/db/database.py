import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from backend.src.config import settings

logger = logging.getLogger("brand-guardian-db")

class Base(DeclarativeBase):
    """Base ORM declarative class."""
    pass

def get_engine_args(db_url: str):
    """Returns database engine arguments depending on dialect."""
    if db_url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
        "pool_recycle": 3600
    }

# Create global engine & sessionmaker factory
engine = create_engine(settings.DATABASE_URL, **get_engine_args(settings.DATABASE_URL))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db(db_engine=None):
    """Creates database tables if they do not exist."""
    import backend.src.db.models  # ensure models are registered with Base.metadata
    target_engine = db_engine or engine
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=target_engine)

def get_db() -> Generator[Session, None, None]:
    """FastAPI Dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
