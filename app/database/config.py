from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, \
    sessionmaker

# Get the project root directory (parent of app folder)
PROJECT_ROOT = Path(__file__).parent.parent.parent
FILES_DIR = PROJECT_ROOT / "files"

# Ensure files directory exists
FILES_DIR.mkdir(exist_ok=True)

# SQLite database file path
DATABASE_FILE = FILES_DIR / "daily_reading.db"
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

# Create engine with SQLite configuration
engine = create_engine(DATABASE_URL,
                       connect_args={
                           "check_same_thread": False},  # Required for SQLite with multiple threads
                       echo=False  # Set to True for SQL query logging
                       )

# Create session factory
SessionLocal = sessionmaker(autocommit=False,
                            autoflush=False,
                            bind=engine)

# Create base class for models
Base = declarative_base()


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
