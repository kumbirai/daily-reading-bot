import logging
import shelve
from typing import Any, Dict, Union

from flask import current_app

from ..extensions import cache
from ..utils.error_handlers import NotFoundError, ValidationError

logger = logging.getLogger(__name__)


def get_readings_db():
    """Get the readings database path from the current app context."""
    return current_app.config['READINGS_DB']


def decode_bytes_in_dict(data: Union[Dict, Any]) -> Union[Dict, Any]:
    """
    Recursively decode bytes objects in a dictionary to strings.
    
    Args:
        data: Dictionary or value to decode
        
    Returns:
        Decoded dictionary or value
    """
    if isinstance(data, bytes):
        return data.decode('utf-8')
    elif isinstance(data, dict):
        return {key: decode_bytes_in_dict(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [decode_bytes_in_dict(item) for item in data]
    return data


def format_date_string(date_str: str) -> str:
    """
    Format date string to match database format.
    
    Args:
        date_str (str): Date string to format in 'Month DD' format (e.g., 'April 24')
        
    Returns:
        str: Formatted date string in 'Month DD' format
        
    Raises:
        ValidationError: If date format is invalid
    """
    try:
        # Remove any extra spaces
        date_str = date_str.strip()

        # Handle Month DD format
        parts = date_str.split()
        if len(parts) != 2:
            raise ValidationError("Date must be in format 'Month DD' (e.g., 'April 24')")

        month, day = parts
        # Validate month
        if not month.isalpha():
            raise ValidationError("Month must be a valid month name")
        # Validate day
        if not day.isdigit() or not (1 <= int(day) <= 31):
            raise ValidationError("Day must be a number between 1 and 31")

        return f"{month.capitalize()} {day}"
    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f"Invalid date format: {str(e)}")


@cache.memoize(timeout=300)  # Cache for 5 minutes
def retrieve_shelf_contents() -> Dict[str, Any]:
    """
    Retrieve all contents from the shelf database.
    
    Returns:
        Dict[str, Any]: Dictionary containing all shelf contents
    """
    with shelve.open(get_readings_db()) as readings:
        readings_dict = dict(readings)
        logger.info(f"Retrieved {len(readings_dict)} items from shelf")
        return decode_bytes_in_dict(readings_dict)


@cache.memoize(timeout=300)  # Cache for 5 minutes
def retrieve_shelf_reading(reading: str) -> Dict[str, Any]:
    """
    Retrieve specific reading from the shelf database.
    
    Args:
        reading (str): Reading key to retrieve
        
    Returns:
        Dict[str, Any]: Dictionary containing the reading data
        
    Raises:
        NotFoundError: If reading is not found
    """
    with shelve.open(get_readings_db()) as readings:
        try:
            this_reading = readings[reading]
            if this_reading:
                reading_content = dict(this_reading).copy()
                data = {reading: decode_bytes_in_dict(reading_content)}
                logger.info(f"Retrieved reading '{reading}' from shelf")
                return data
        except KeyError:
            logger.warning(f"Reading '{reading}' not found in shelf")
            raise NotFoundError(f"Reading '{reading}' not found")


@cache.memoize(timeout=300)  # Cache for 5 minutes
def retrieve_shelf_date(date: str) -> Dict[str, Any]:
    """
    Retrieve readings for a specific date from the shelf database.
    
    Args:
        date (str): Date to retrieve readings for
        
    Returns:
        Dict[str, Any]: Dictionary containing readings for the date
        
    Raises:
        NotFoundError: If no readings found for date
        ValidationError: If date format is invalid
    """
    formatted_date = format_date_string(date)
    with shelve.open(get_readings_db()) as readings:
        readings_dict = dict(readings)
        data = {}

        for key, value in readings_dict.items():
            date_value = dict(value.get(formatted_date, {})).copy()
            if date_value:
                data[key] = {formatted_date: decode_bytes_in_dict(date_value)}

        if not data:
            logger.warning(f"No readings found for date '{formatted_date}'")
            raise NotFoundError(f"No readings found for date '{formatted_date}'. Please try a different date or check if the readings have been scraped.")

        logger.info(f"Retrieved {len(data)} readings for date '{formatted_date}'")
        return data
