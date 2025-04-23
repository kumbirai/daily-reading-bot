import json
import logging
import shelve
from typing import Dict, Any
from flask import current_app
from ..utils.error_handlers import DatabaseError, NotFoundError
from ..extensions import cache

logger = logging.getLogger(__name__)

def get_readings_db():
    """Get the readings database path from the current app context."""
    return current_app.config['READINGS_DB']

def format_date_string(date_str: str) -> str:
    """
    Format date string to match database format.
    
    Args:
        date_str (str): Date string to format
        
    Returns:
        str: Formatted date string
    """
    # Remove any extra spaces and ensure proper capitalization
    parts = date_str.strip().split()
    if len(parts) != 2:
        raise ValidationError("Date must be in format 'Month DD'")
    
    month, day = parts
    return f"{month.capitalize()} {day}"

@cache.memoize(timeout=300)  # Cache for 5 minutes
def retrieve_shelf_contents() -> Dict[str, Any]:
    """
    Retrieve all contents from the shelf database.
    
    Returns:
        Dict[str, Any]: Dictionary containing all shelf contents
        
    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with shelve.open(get_readings_db()) as readings:
            readings_dict = dict(readings)
            logger.info(f"Retrieved {len(readings_dict)} items from shelf")
            return readings_dict
    except Exception as e:
        logger.error(f"Error retrieving shelf contents: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to retrieve shelf contents")

@cache.memoize(timeout=300)  # Cache for 5 minutes
def retrieve_shelf_reading(reading: str) -> Dict[str, Any]:
    """
    Retrieve specific reading from the shelf database.
    
    Args:
        reading (str): Reading key to retrieve
        
    Returns:
        Dict[str, Any]: Dictionary containing the reading data
        
    Raises:
        DatabaseError: If database operation fails
        NotFoundError: If reading is not found
    """
    try:
        with shelve.open(get_readings_db()) as readings:
            try:
                this_reading = readings[reading]
                if this_reading:
                    reading_content = dict(this_reading).copy()
                    data = {reading: reading_content}
                    logger.info(f"Retrieved reading '{reading}' from shelf")
                    return data
            except KeyError:
                logger.warning(f"Reading '{reading}' not found in shelf")
                raise NotFoundError(f"Reading '{reading}' not found")
    except Exception as e:
        logger.error(f"Error retrieving reading '{reading}': {str(e)}", exc_info=True)
        raise DatabaseError(f"Failed to retrieve reading '{reading}'")

@cache.memoize(timeout=300)  # Cache for 5 minutes
def retrieve_shelf_date(date: str) -> Dict[str, Any]:
    """
    Retrieve readings for a specific date from the shelf database.
    
    Args:
        date (str): Date to retrieve readings for
        
    Returns:
        Dict[str, Any]: Dictionary containing readings for the date
        
    Raises:
        DatabaseError: If database operation fails
        NotFoundError: If no readings found for date
    """
    try:
        formatted_date = format_date_string(date)
        with shelve.open(get_readings_db()) as readings:
            readings_dict = dict(readings)
            data = {}
            
            for key, value in readings_dict.items():
                date_value = dict(value.get(formatted_date, {})).copy()
                if date_value:
                    data[key] = {formatted_date: date_value}
                    
            if not data:
                logger.warning(f"No readings found for date '{formatted_date}'")
                raise NotFoundError(f"No readings found for date '{formatted_date}'")
                
            logger.info(f"Retrieved {len(data)} readings for date '{formatted_date}'")
            return data
    except Exception as e:
        logger.error(f"Error retrieving readings for date '{date}': {str(e)}", exc_info=True)
        raise DatabaseError(f"Failed to retrieve readings for date '{date}'")

if __name__ == "__main__":
    logging.info(retrieve_shelf_contents())
    logging.info(retrieve_shelf_reading('dr'))
    logging.info(retrieve_shelf_date('April 16'))
