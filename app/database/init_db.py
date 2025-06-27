import logging

from app.database.config import engine
from app.models.models import Base

logger = logging.getLogger(__name__)


def init_db():
    """Initialize the database by creating all tables."""
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully!")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        raise


if __name__ == "__main__":
    from app.utils.logging_config import setup_logging

    setup_logging()
    init_db()
