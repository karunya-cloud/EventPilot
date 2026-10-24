"""Database engine and session management for EventPilot AI."""
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from src.config import settings

logger = logging.getLogger("eventpilot.db")

Base = declarative_base()

# Determine connect args (e.g. check_same_thread for SQLite)
connect_args = {}
if "sqlite" in settings.DATABASE_URL:
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Context-manager generator for FastAPI and tool dependencies."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create all tables in the database."""
    from src.db import models  # ensure models are imported
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")
