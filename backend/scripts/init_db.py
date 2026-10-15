"""
Database initialization and migration runner for Brand Guardian AI (Phase 7).
Ensures PostgreSQL schema is fully initialized and stamped at Alembic head.
"""
import sys
import logging
from alembic.config import Config
from alembic import command
from backend.src.db.database import init_db, engine
from backend.src.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("brand-guardian-db-init")

def run_init_and_migrations():
    """
    Initializes PostgreSQL tables and synchronizes Alembic version tracking.
    """
    safe_db = settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL
    logger.info(f"Initializing database at: {safe_db}")

    try:
        # 1. Initialize tables from declarative Base metadata
        init_db(engine)
        logger.info("Database tables initialized successfully via Declarative Base.")

        # 2. Check and stamp Alembic head
        alembic_cfg = Config("alembic.ini")
        command.stamp(alembic_cfg, "head")
        logger.info("Alembic migration version stamped at 'head' successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_init_and_migrations()
