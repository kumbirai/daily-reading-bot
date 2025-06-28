#!/usr/bin/env python3
"""
Command-line script to query readings from the SQLite database.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, \
    Dict, \
    List, \
    Optional

# Add the app directory to the path so we can import the models and services
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import joinedload
from app.database.init_db import init_db
from app.services.database_service import DatabaseService
from app.models.models import Reading


def datetime_to_iso(dt: datetime) -> str:
    """Convert datetime object to ISO format string."""
    if dt is None:
        return None
    return dt.isoformat()


def reading_to_dict(reading: Reading) -> Dict[str, Any]:
    """Convert a Reading model to a dictionary."""
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
        'modified_at': datetime_to_iso(reading.modified_at),
        'recipients': [
            {
                'wa_id': recipient.wa_id,
                'sent': datetime_to_iso(recipient.sent)
            }
            for recipient in reading.recipients
        ] if reading.recipients else []
    }


def query_readings(limit: Optional[int] = None,
                   reading_type: Optional[str] = None,
                   date_from: Optional[str] = None,
                   date_to: Optional[str] = None,
                   order_by: str = 'created_at_desc') -> List[Dict[str, Any]]:
    """
    Query readings from the database with various filters.
    
    Args:
        limit (Optional[int]): Maximum number of readings to retrieve (None for no limit)
        reading_type (Optional[str]): Filter by reading type (dr, jft, spad)
        date_from (Optional[str]): Filter by date from (format: YYYY-MM-DD)
        date_to (Optional[str]): Filter by date to (format: YYYY-MM-DD)
        order_by (str): Order by field and direction (field_direction)
        
    Returns:
        List[Dict[str, Any]]: List of reading dictionaries
    """
    try:
        with DatabaseService() as db_service:
            # Start with base query and eagerly load recipients
            query = db_service.db.query(Reading).options(joinedload(Reading.recipients))

            # Apply filters
            if reading_type:
                query = query.filter(Reading.reading_type == reading_type)

            if date_from:
                query = query.filter(Reading.date >= date_from)

            if date_to:
                query = query.filter(Reading.date <= date_to)

            # Apply ordering
            if order_by == 'created_at_desc':
                query = query.order_by(Reading.created_at.desc())
            elif order_by == 'created_at_asc':
                query = query.order_by(Reading.created_at.asc())
            elif order_by == 'date_desc':
                query = query.order_by(Reading.date.desc())
            elif order_by == 'date_asc':
                query = query.order_by(Reading.date.asc())
            elif order_by == 'id_desc':
                query = query.order_by(Reading.id.desc())
            elif order_by == 'id_asc':
                query = query.order_by(Reading.id.asc())
            else:
                # Default to created_at_desc
                query = query.order_by(Reading.created_at.desc())

            # Apply limit only if specified
            if limit is not None:
                query = query.limit(limit)

            # Execute query
            readings = query.all()

            # Convert to dictionaries
            reading_dicts = [reading_to_dict(reading) for reading in readings]

            return reading_dicts

    except Exception as e:
        print(f"Error querying readings from database: {e}")
        return []


def print_readings(readings: List[Dict[str, Any]], output_format: str = 'json'):
    """
    Print readings in the specified format.
    
    Args:
        readings (List[Dict[str, Any]]): List of reading dictionaries
        output_format (str): Output format ('json', 'summary', 'table')
    """
    if not readings:
        print("No readings found matching the criteria.")
        return

    if output_format == 'json':
        # Print as JSON
        result = {
            'total_readings': len(readings),
            'readings': readings
        }
        print(json.dumps(result,
                         indent=2,
                         ensure_ascii=False))

    elif output_format == 'summary':
        # Print summary
        print(f"Total readings: {len(readings)}")

        # Group by reading type
        reading_types = {}
        for reading in readings:
            reading_type = reading['reading_type']
            if reading_type not in reading_types:
                reading_types[reading_type] = 0
            reading_types[reading_type] += 1

        print(f"Reading types:")
        for reading_type, count in reading_types.items():
            print(f"  {reading_type}: {count}")

        # Show date range
        dates = [reading['date'] for reading in readings if reading['date']]
        if dates:
            print(f"Date range: {min(dates)} to {max(dates)}")

    elif output_format == 'table':
        # Print as table
        print(f"{'ID':<5} {'Type':<5} {'Date':<12} {'Heading':<50}")
        print("-" * 80)
        for reading in readings:
            heading = reading['heading'][:47] + "..." if len(reading['heading']) > 50 else reading['heading']
            print(f"{reading['id']:<5} {reading['reading_type']:<5} {reading['date']:<12} {heading}")


def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description='Query readings from SQLite database')
    parser.add_argument('--limit',
                        type=int,
                        help='Maximum number of readings to retrieve (default: no limit)')
    parser.add_argument('--type',
                        dest='reading_type',
                        choices=['dr',
                                 'jft',
                                 'spad'],
                        help='Filter by reading type')
    parser.add_argument('--date-from',
                        help='Filter by date from (format: YYYY-MM-DD)')
    parser.add_argument('--date-to',
                        help='Filter by date to (format: YYYY-MM-DD)')
    parser.add_argument('--order-by',
                        default='created_at_desc',
                        choices=['created_at_desc',
                                 'created_at_asc',
                                 'date_desc',
                                 'date_asc',
                                 'id_desc',
                                 'id_asc'],
                        help='Order by field and direction (default: created_at_desc)')
    parser.add_argument('--format',
                        choices=['json',
                                 'summary',
                                 'table'],
                        default='json',
                        help='Output format (default: json)')

    args = parser.parse_args()

    # Initialize database connection
    print("Initializing database connection...")
    init_db()
    print("Database connection initialized!")

    # Query readings
    limit_text = f"limit={args.limit}" if args.limit else "no limit"
    print(f"Querying readings with {limit_text}, type={args.reading_type}, order_by={args.order_by}...")
    readings = query_readings(
        limit=args.limit,
        reading_type=args.reading_type,
        date_from=args.date_from,
        date_to=args.date_to,
        order_by=args.order_by
    )

    # Print results
    print_readings(readings,
                   args.format)


if __name__ == "__main__":
    main()
