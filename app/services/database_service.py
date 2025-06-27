import logging
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from ..database.config import get_db
from ..models.models import Reading, Recipient, utc_now

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service class for handling database operations with Reading models."""

    def __init__(self):
        self.db: Optional[Session] = None

    def __enter__(self):
        """Context manager entry."""
        self.db = next(get_db())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.db:
            self.db.close()

    def store_reading_dict(self, reading_dict: Dict[str, Any]) -> Optional[Reading]:
        """
        Store a dictionary as a Reading model in the database.
        
        Args:
            reading_dict (Dict[str, Any]): Dictionary containing reading data
            
        Returns:
            Optional[Reading]: The created Reading model, or None if operation fails
            
        Raises:
            Exception: If database operation fails
        """
        try:
            if not self.db:
                raise Exception("Database session not initialized")

            # Check if reading already exists for this date and type
            existing_reading = self.db.query(Reading).filter(Reading.date == reading_dict.get('date'), Reading.reading_type == reading_dict.get('reading_type')).first()

            if existing_reading:
                logger.info(f"Reading already exists for {reading_dict.get('reading_type')} on {reading_dict.get('date')}")
                return existing_reading

            # Create new Reading model from dictionary
            reading = Reading(reading_type=reading_dict.get('reading_type', ''), date=reading_dict.get('date', ''), heading=reading_dict.get('heading', ''), quote=reading_dict.get('quote', ''), source=reading_dict.get('source', ''), narrative=reading_dict.get('narrative', ''), affirmation=reading_dict.get('affirmation', ''))

            self.db.add(reading)
            self.db.commit()
            self.db.refresh(reading)

            logger.info(f"Successfully stored reading for {reading.reading_type} on {reading.date}")
            return reading

        except Exception as e:
            logger.error(f"Error storing reading in database: {str(e)}", exc_info=True)
            if self.db:
                self.db.rollback()
            raise

    def add_recipient_to_reading(self, reading_id: int, wa_id: str, sent: Optional[datetime] = None) -> Optional[Recipient]:
        """
        Add a recipient to an existing reading.
        
        Args:
            reading_id (int): ID of the reading
            wa_id (str): WhatsApp ID of the recipient
            sent (Optional[datetime]): Timestamp when the recipient was sent the reading
            
        Returns:
            Optional[Recipient]: The created Recipient model, or None if operation fails
            
        Raises:
            Exception: If database operation fails
        """
        try:
            if not self.db:
                raise Exception("Database session not initialized")

            # Check if recipient already exists for this reading and wa_id
            existing_recipient = self.db.query(Recipient).filter(Recipient.reading_id == reading_id, Recipient.wa_id == wa_id).first()

            if existing_recipient:
                logger.info(f"Recipient {wa_id} already exists for reading {reading_id}")
                return existing_recipient

            # Create new Recipient model
            recipient = Recipient(reading_id=reading_id, wa_id=wa_id, sent=sent if sent else utc_now())

            self.db.add(recipient)
            self.db.commit()
            self.db.refresh(recipient)

            logger.info(f"Successfully added recipient {wa_id} to reading {reading_id}")
            return recipient

        except Exception as e:
            logger.error(f"Error adding recipient to reading: {str(e)}", exc_info=True)
            if self.db:
                self.db.rollback()
            raise

    def get_reading_by_date_and_type(self, date: str, reading_type: str) -> Optional[Reading]:
        """
        Get a reading by date and type.
        
        Args:
            date (str): Date of the reading
            reading_type (str): Type of the reading
            
        Returns:
            Optional[Reading]: The Reading model if found, None otherwise
        """
        try:
            if not self.db:
                raise Exception("Database session not initialized")

            reading = self.db.query(Reading).filter(Reading.date == date, Reading.reading_type == reading_type).first()

            return reading

        except Exception as e:
            logger.error(f"Error retrieving reading from database: {str(e)}", exc_info=True)
            raise

    def store_reading_with_recipient(self, reading_dict: Dict[str, Any], wa_id: str) -> Optional[Reading]:
        """
        Store a reading dictionary and add a recipient in a single transaction.
        
        Args:
            reading_dict (Dict[str, Any]): Dictionary containing reading data
            wa_id (str): WhatsApp ID of the recipient
            
        Returns:
            Optional[Reading]: The created Reading model, or None if operation fails
        """
        try:
            # Store the reading
            reading = self.store_reading_dict(reading_dict)

            if reading:
                # Add the recipient
                self.add_recipient_to_reading(reading.id, wa_id)

            return reading

        except Exception as e:
            logger.error(f"Error storing reading with recipient: {str(e)}", exc_info=True)
            raise
