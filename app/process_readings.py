#!/usr/bin/env python3
"""
Script to process readings from the shelf database and extract structured data.
"""

import json
import os
import shelve
import sys
from datetime import date, \
    datetime
from typing import Optional

# Add the app directory to the path so we can import the loaders
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.loader.daily_reading_loader import parse_reading_to_dict as parse_daily_reading
from app.loader.just_for_today_loader import parse_reading_to_dict as parse_jft_reading
from app.loader.spiritual_principal_a_day_loader import parse_reading_to_dict as parse_spad_reading

# Database imports
from app.database.init_db import init_db
from app.services.database_service import DatabaseService


def parse_date_string(date_str: str) -> Optional[date]:
    """
    Parse date string in format 'Month Day' (e.g., 'April 11') to date object.
    
    Args:
        date_str (str): Date string in format 'Month Day'
        
    Returns:
        date: Parsed date object or None if parsing fails
    """
    try:
        # Add current year to the date string
        current_year = datetime.now().year
        full_date_str = f"{date_str} {current_year}"

        # Parse the date
        parsed_date = datetime.strptime(full_date_str,
                                        "%B %d %Y").date()

        # If the parsed date is in the future, it might be from last year
        if parsed_date > date.today():
            parsed_date = datetime.strptime(f"{date_str} {current_year - 1}",
                                            "%B %d %Y").date()

        return parsed_date
    except ValueError as e:
        print(f"Error parsing date '{date_str}': {e}")
        return None


def find_first_date_key(db) -> Optional[str]:
    """
    Find the first date_key from the database.
    
    Args:
        db: The shelf database object
        
    Returns:
        str: The first date_key found, or None if no dates found
    """
    reading_types = ['dr',
                     'jft',
                     'spad']

    for reading_type in reading_types:
        if reading_type in db:
            reading_data = db[reading_type]
            if isinstance(reading_data,
                          dict) and reading_data:
                # Get the first date_key from this reading type
                first_date = list(reading_data.keys())[0]
                return first_date

    return None


def get_all_date_keys_sorted(db) -> list:
    """
    Get all date keys from the database and sort them in chronological order.
    
    Args:
        db: The shelf database object
        
    Returns:
        list: Sorted list of date keys in chronological order
    """
    reading_types = ['dr',
                     'jft',
                     'spad']
    all_date_keys = set()

    # Collect all date keys from all reading types
    for reading_type in reading_types:
        if reading_type in db:
            reading_data = db[reading_type]
            if isinstance(reading_data,
                          dict):
                all_date_keys.update(reading_data.keys())

    # Convert to list and sort chronologically
    date_keys_list = list(all_date_keys)

    # Sort by parsing the dates
    def date_key_to_date(date_key):
        parsed_date = parse_date_string(date_key)
        return parsed_date if parsed_date else date.max  # Put invalid dates at the end

    date_keys_list.sort(key=date_key_to_date)

    return date_keys_list


def process_readings():
    """
    Main function to process readings from the shelf database.
    """
    # Initialize database first
    print("Initializing database...")
    init_db()
    print("Database initialized successfully!")

    # Paths
    shelf_path = os.path.join(os.path.dirname(__file__),
                              '..',
                              'files',
                              'readings_db')
    output_path = os.path.join(os.path.dirname(__file__),
                               '..',
                               'files',
                               'extractresults.json')

    # Initialize results dictionary
    results = {}
    db_save_count = 0

    try:
        # Open the shelf database
        with shelve.open(shelf_path,
                         'r') as db:
            print(f"Opened shelf database: {shelf_path}")

            # Get all keys in the database
            all_keys = list(db.keys())
            print(f"Found {len(all_keys)} keys in database: {all_keys}")

            # Get all date keys sorted in chronological order
            all_date_keys = get_all_date_keys_sorted(db)
            if not all_date_keys:
                print("No date keys found in database")
                return

            print(f"\nFound {len(all_date_keys)} date keys in chronological order:")
            for i, date_key in enumerate(all_date_keys[:10]):  # Show first 10
                print(f"  {i + 1}. {date_key}")
            if len(all_date_keys) > 10:
                print(f"  ... and {len(all_date_keys) - 10} more dates")

            # Define reading types and their corresponding parsers
            reading_types = {
                'dr': parse_daily_reading,
                'jft': parse_jft_reading,
                'spad': parse_spad_reading}

            # Process each date in chronological order
            for date_index, date_key in enumerate(all_date_keys,
                                                  1):
                print(f"\n{'=' * 60}")
                print(f"Processing date {date_index}/{len(all_date_keys)}: {date_key}")
                print(f"{'=' * 60}")

                # Process each reading type for this date
                for reading_type, parser_func in reading_types.items():
                    if reading_type in db:
                        print(f"\nProcessing {reading_type} reading for date: {date_key}")

                        # Get the data for this reading type
                        reading_data = db[reading_type]

                        if isinstance(reading_data,
                                      dict) and date_key in reading_data:
                            date_data = reading_data[date_key]

                            if isinstance(date_data,
                                          dict) and 'text' in date_data:
                                text_content = date_data['text']

                                if text_content:
                                    parsed_result = parser_func(text_content)
                                    if parsed_result:
                                        # Store result with date and reading type
                                        if date_key not in results:
                                            results[date_key] = {}
                                        results[date_key][reading_type] = parsed_result
                                        print(f"    Successfully parsed {reading_type}")

                                        # Get extract_date from shelf data if available
                                        extract_date = None
                                        if 'extract_date' in date_data:
                                            try:
                                                extract_date = date_data['extract_date']
                                                if isinstance(extract_date,
                                                              str):
                                                    # Parse string date to datetime
                                                    extract_date = datetime.fromisoformat(extract_date.replace('Z',
                                                                                                               '+00:00'))
                                            except Exception as e:
                                                print(f"    Warning: Could not parse extract_date '{date_data.get('extract_date')}': {e}")

                                        # Save to database using DatabaseService
                                        try:
                                            with DatabaseService() as db_service:
                                                # Pass extract_date as created_at if available
                                                stored_reading = db_service.store_reading_dict(parsed_result,
                                                                                               created_at=extract_date)
                                                if stored_reading:
                                                    db_save_count += 1
                                                    print(f"    Saved {reading_type} reading to database with ID: {stored_reading.id}")

                                                    # Process recipients if available
                                                    if 'recipients' in date_data and isinstance(date_data['recipients'],
                                                                                                list):
                                                        recipients_list = date_data['recipients']
                                                        print(f"    Found {len(recipients_list)} recipients for {reading_type}")

                                                        for recipient_data in recipients_list:
                                                            try:
                                                                wa_id = recipient_data.get('wa_id')
                                                                sent_str = recipient_data.get('sent')
                                                                sent_timestamp = None

                                                                # Parse sent timestamp if available
                                                                if sent_str:
                                                                    try:
                                                                        if isinstance(sent_str,
                                                                                      str):
                                                                            sent_timestamp = datetime.fromisoformat(sent_str.replace('Z',
                                                                                                                                     '+00:00'))
                                                                        elif isinstance(sent_str,
                                                                                        datetime):
                                                                            sent_timestamp = sent_str
                                                                    except Exception as e:
                                                                        print(f"      Warning: Could not parse sent timestamp '{sent_str}': {e}")
                                                                else:
                                                                    print(f"      Warning: Invalid recipient data format: {type(recipient_data)}")
                                                                    continue

                                                                if wa_id:
                                                                    recipient = db_service.add_recipient_to_reading(stored_reading.id,
                                                                                                                    wa_id,
                                                                                                                    sent_timestamp)
                                                                    if recipient:
                                                                        print(f"      Added recipient: {wa_id}" + (f" (sent: {sent_timestamp})" if sent_timestamp else ""))
                                                                    else:
                                                                        print(f"      Recipient {wa_id} already exists")
                                                                else:
                                                                    print(f"      Warning: No wa_id found in recipient data: {recipient_data}")
                                                            except Exception as e:
                                                                print(f"      Error adding recipient {recipient_data}: {e}")
                                                    else:
                                                        print(f"    No recipients found for {reading_type}")
                                                else:
                                                    print(f"    Reading already exists for {reading_type}")
                                        except Exception as e:
                                            print(f"    Error saving {reading_type} reading to database: {e}")
                                    else:
                                        print(f"    Failed to parse {reading_type}")
                                else:
                                    print(f"    No text content found for {reading_type}")
                            else:
                                print(f"    Invalid data structure for date {date_key}")
                        else:
                            print(f"    No data found for {reading_type} on date {date_key}")
                    else:
                        print(f"\nNo {reading_type} data found in database")

        # Save results to JSON file
        print(f"\nSaving results to: {output_path}")
        with open(output_path,
                  'w',
                  encoding='utf-8') as f:
            json.dump(results,
                      f,
                      indent=2,
                      ensure_ascii=False)

        print(f"Successfully saved {len(results)} date entries to {output_path}")

        # Print summary
        total_readings = sum(len(date_data) for date_data in results.values())
        print(f"\nSummary:")
        print(f"  Total dates processed: {len(results)}")
        print(f"  Total readings extracted: {total_readings}")
        print(f"  Total readings saved to database: {db_save_count}")

        # Show first few results as example
        if results:
            print(f"\nFirst result example:")
            first_date = list(results.keys())[0]
            print(f"  Date: {first_date}")
            for reading_type, data in results[first_date].items():
                print(f"    {reading_type}: {data.get('heading', 'No heading')[:50]}...")

    except Exception as e:
        print(f"Error processing readings: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    process_readings()
