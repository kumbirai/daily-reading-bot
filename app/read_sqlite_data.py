#!/usr/bin/env python3
"""
Script to read readings from the SQLite database and print them as JSON.
"""

import json
import os
import sys
from datetime import datetime
from typing import Any, \
    Dict, \
    List

# Add the app directory to the path so we can import the models and services
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.init_db import init_db
from app.services.database_service import DatabaseService
from app.models.models import Reading


def datetime_to_iso(dt: datetime) -> str:
    """
    Convert datetime object to ISO format string.
    
    Args:
        dt (datetime): Datetime object to convert
        
    Returns:
        str: ISO format string
    """
    if dt is None:
        return None
    return dt.isoformat()


def reading_to_dict(reading: Reading) -> Dict[str, Any]:
    """
    Convert a Reading model to a dictionary.
    
    Args:
        reading (Reading): Reading model instance
        
    Returns:
        Dict[str, Any]: Dictionary representation of the reading
    """
    return {
        'id': reading.id,
        'reading_type': reading.reading_type,
        'date': reading.date,
        'heading': reading.heading,
        'quote': reading.quote,
        'source': reading.source,
        'narrative': reading.narrative,
        'affirmation': reading.affirmation,
        'created_at': datetime_to_iso(reading.created_at),
        'modified_at': datetime_to_iso(reading.modified_at)
    }


def get_readings_from_database(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get readings from the database.
    
    Args:
        limit (int): Maximum number of readings to retrieve
        
    Returns:
        List[Dict[str, Any]]: List of reading dictionaries
    """
    try:
        with DatabaseService() as db_service:
            # Query the database for readings, ordered by created_at descending
            readings = db_service.db.query(Reading).order_by(Reading.created_at.desc()).limit(limit).all()

            # Convert to dictionaries
            reading_dicts = [reading_to_dict(reading) for reading in readings]

            return reading_dicts

    except Exception as e:
        print(f"Error retrieving readings from database: {e}")
        return []


def print_readings_as_json(limit: int = 50):
    """
    Print readings from the database as JSON.
    
    Args:
        limit (int): Maximum number of readings to retrieve and print
    """
    print(f"Retrieving first {limit} readings from SQLite database...")

    # Get readings from database
    readings = get_readings_from_database(limit)

    if not readings:
        print("No readings found in database.")
        return

    # Create result structure
    result = {
        'total_readings': len(readings),
        'limit': limit,
        'readings': readings
    }

    # Print as formatted JSON
    print("\n" + "=" * 80)
    print("READINGS FROM SQLITE DATABASE")
    print("=" * 80)
    print(json.dumps(result,
                     indent=2,
                     ensure_ascii=False))
    print("=" * 80)

    # Print summary
    print(f"\nSummary:")
    print(f"  Total readings retrieved: {len(readings)}")

    # Group by reading type
    reading_types = {}
    for reading in readings:
        reading_type = reading['reading_type']
        if reading_type not in reading_types:
            reading_types[reading_type] = 0
        reading_types[reading_type] += 1

    print(f"  Reading types:")
    for reading_type, count in reading_types.items():
        print(f"    {reading_type}: {count}")

    # Show date range
    if readings:
        dates = [reading['date'] for reading in readings if reading['date']]
        if dates:
            print(f"  Date range: {min(dates)} to {max(dates)}")


def main():
    """
    Main function to run the script.
    """
    # Initialize database connection
    print("Initializing database connection...")
    init_db()
    print("Database connection initialized!")

    # Print readings as JSON
    print_readings_as_json(50)


if __name__ == "__main__":
    main()
