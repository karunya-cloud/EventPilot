"""Pytest fixtures and configuration."""
import os
import sys
from pathlib import Path
import pytest

# Ensure root directory is on PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

TEST_DB_PATH = ROOT_DIR / "test_eventpilot.db"
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

@pytest.fixture(scope="session", autouse=True)
def clean_test_db():
    from src.db.session import Base, engine, init_db
    from src.db.seed import seed_database
    # Reset schema for a clean test suite run
    Base.metadata.drop_all(bind=engine)
    init_db()
    seed_database()
    yield
    # Cleanup after session
    try:
        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink(missing_ok=True)
    except Exception:
        pass

