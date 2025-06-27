import datetime
import logging
import shelve
import time
from datetime import date
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List

import requests
from bs4 import BeautifulSoup
from flask import current_app
from requests.exceptions import RequestException

from .database_service import DatabaseService
from ..extensions import cache
from ..loader.daily_reading_loader import parse_reading_to_dict as dr_loader
from ..loader.just_for_today_loader import parse_reading_to_dict as jft_loader
from ..loader.spiritual_principal_a_day_loader import parse_reading_to_dict as spad_loader
from ..utils.error_handlers import DatabaseError, ValidationError

logger = logging.getLogger(__name__)

FORMAT = '%B %d'
DR_KEY = 'dr'
JFT_KEY = 'jft'
SPAD_KEY = 'spad'


def retry_on_failure(max_attempts: int = None, delay: int = None):
    """
    Decorator for retrying functions on failure.
    
    Args:
        max_attempts (int): Maximum number of retry attempts
        delay (int): Delay between retries in seconds
    """

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = max_attempts or current_app.config['READING_RETRY_ATTEMPTS']
            retry_delay = delay or current_app.config['READING_RETRY_DELAY']

            for attempt in range(attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == attempts - 1:
                        raise
                    logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
            return None

        return wrapper

    return decorator


class ReadingStorage:
    """Class for handling reading storage operations."""

    def __init__(self):
        self.db_path = get_readings_db()
        self.db_service = DatabaseService()

    def store_reading(self, file_text: str, key: str, today: str) -> None:
        """
        Store reading in database.
        
        Args:
            file_text (str): Reading text
            key (str): Reading key
            today (str): Date string
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            with shelve.open(self.db_path, writeback=True) as readings_shelf:
                readings = readings_shelf.get(key, {})
                readings[today] = {"text": file_text, "extract_date": datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(), "recipients": []}
                readings_shelf[key] = readings
            reading_loaders = {DR_KEY: dr_loader, JFT_KEY: jft_loader, SPAD_KEY: spad_loader}
            reading_dict = reading_loaders[key](file_text)
            if reading_dict:
                try:
                    with self.db_service as db_service:
                        db_service.store_reading_dict(reading_dict)
                except Exception as e:
                    logger.warning(f"Failed to store reading to SQLite database: {str(e)}")
        except Exception as e:
            logger.error(f"Error storing reading in database: {str(e)}", exc_info=True)
            raise DatabaseError("Failed to store reading in database")

    @cache.memoize(timeout=3600)  # Cache for 1 hour
    def retrieve_readings(self, key: str) -> Dict[str, Any]:
        """
        Retrieve readings from database.
        
        Args:
            key (str): Reading key
            
        Returns:
            Dict[str, Any]: Retrieved readings
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            with shelve.open(self.db_path) as readings_shelf:
                return readings_shelf.get(key, {})
        except Exception as e:
            logger.error(f"Error retrieving readings from database: {str(e)}", exc_info=True)
            raise DatabaseError("Failed to retrieve readings from database")

    def add_recipient(self, today: str, key: str, wa_id: str) -> None:
        """
        Add recipient to reading.
        
        Args:
            today (str): Date string
            key (str): Reading key
            wa_id (str): WhatsApp ID
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            with shelve.open(self.db_path, writeback=True) as readings_shelf:
                readings = readings_shelf.get(key)
                recipient = {"wa_id": wa_id, "sent": datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()}
                recipients = list(readings.get(today).get("recipients"))
                recipients.append(recipient.copy())
                readings.get(today)["recipients"] = recipients
                readings_shelf[key] = readings

                # Store recipient in SQLite database using DatabaseService
                with self.db_service as db_service:
                    # First, get the reading by date and type
                    reading = db_service.get_reading_by_date_and_type(today, key)
                    if reading:
                        # Convert sent timestamp string to datetime object
                        sent_datetime = datetime.datetime.fromisoformat(recipient["sent"])
                        # Add recipient to the reading
                        db_service.add_recipient_to_reading(reading.id, wa_id, sent_datetime)
                        logger.info(f"Added recipient {wa_id} to {key} reading for {today}")
                    else:
                        logger.warning(f"Reading not found for {key} on {today}, skipping SQLite recipient addition")
        except Exception as e:
            logger.error(f"Error adding recipient: {str(e)}", exc_info=True)
            raise DatabaseError("Failed to add recipient")


class ReadingScraper:
    """Class for scraping daily readings from various sources."""

    def __init__(self):
        self.files_dir = Path(current_app.config['READING_FILES_DIR'])
        self.dr_filename = self.files_dir / current_app.config['DR_FILENAME']
        self.jft_filename = self.files_dir / current_app.config['JFT_FILENAME']
        self.spad_filename = self.files_dir / current_app.config['SPAD_FILENAME']
        self.reflections_filename = self.files_dir / current_app.config['REFLECTIONS_FILENAME']
        self.storage = ReadingStorage()
        self.db_service = DatabaseService()

    @retry_on_failure()
    def parse_table(self, url: str) -> List[str]:
        """
        Parse HTML table from the given URL.
        
        Args:
            url (str): URL to fetch and parse
            
        Returns:
            List[str]: List of parsed table contents
            
        Raises:
            ValidationError: If URL is invalid or table parsing fails
        """
        try:
            response = requests.get(url, timeout=current_app.config['READING_TIMEOUT'])
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            rows = soup.find_all('tr')

            if not rows:
                raise ValidationError(f"No table rows found at {url}")

            data = []
            for row in rows:
                td = row.find('td')
                if not td:
                    continue

                for br_tag in td.find_all('br'):
                    new_tag = soup.new_tag("b")
                    new_tag.string = '\n'
                    br_tag.replace_with(new_tag)

                text = td.text
                data.append(text)

            return data
        except RequestException as e:
            logger.error(f"Error fetching or parsing table from {url}: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to fetch or parse table from {url}")

    def extract_daily_reflection(self) -> str:
        """
        Extract daily reflection from file.
        
        Returns:
            str: Daily reflection text
            
        Raises:
            DatabaseError: If file operation fails
            ValidationError: If daily reflection not found
        """
        try:
            with open(self.reflections_filename, 'rt', encoding="utf-8") as reflections:
                contents = reflections.read()

            today = date.strftime(date.today(), FORMAT)
            formatted_date = date.today().strftime('%B %d')
            formatted_date = formatted_date.replace(" 0", " ")
            start = contents.find(f"_*{formatted_date}*_")

            if start == -1:
                raise ValidationError("Daily reflection not found for today")

            end = contents.find("_*", start + 1)
            if end == -1:
                end = len(contents)

            today_readings = contents[start:end].strip()

            self._write_to_file([today_readings], self.dr_filename)
            self.storage.store_reading(today_readings, DR_KEY, today)
            return today_readings
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error extracting daily reflection: {str(e)}", exc_info=True)
            raise DatabaseError("Failed to extract daily reflection")

    @retry_on_failure()
    def parse_jft_page(self) -> str:
        """
        Parse Just for Today page.

        Returns:
            str: Parsed JFT content

        Raises:
            ValidationError: If parsing fails
        """
        try:
            jft_rows = self.parse_table(current_app.config['JFT_URL'])

            if not jft_rows:
                raise ValidationError("No content found on JFT page")

            content = self._extract_content('❇️ *Just For Today* ❇️', jft_rows)
            content.append('\n\n' + self._format_jft_footer(jft_rows[6]))

            self._write_to_file(content, self.jft_filename)

            file_text = self._read_text_file(self.jft_filename)
            today = date.strftime(date.today(), FORMAT)

            if file_text.find(today) != -1:
                self.storage.store_reading(file_text, JFT_KEY, today)
                return file_text

            raise ValidationError("JFT content not found for today")
        except Exception as e:
            logger.error(f"Error parsing JFT page: {str(e)}", exc_info=True)
            raise ValidationError("Failed to parse JFT page")

    @retry_on_failure()
    def parse_spad_page(self) -> str:
        """
        Parse Spiritual Principle A Day page.

        Returns:
            str: Parsed SPAD content

        Raises:
            ValidationError: If parsing fails
        """
        try:
            spad_rows = self.parse_table(current_app.config['SPAD_URL'])

            if not spad_rows:
                raise ValidationError("No content found on SPAD page")

            content = self._extract_content('🔷 *Spiritual Principle A Day* 🔷', spad_rows)
            content.append('\n\n' + spad_rows[6].strip())
            content.append('\n\n' + self._format_spad_footer(spad_rows[7]))

            self._write_to_file(content, self.spad_filename)

            file_text = self._read_text_file(self.spad_filename)
            today = date.strftime(date.today(), FORMAT)

            if file_text.find(today) != -1:
                self.storage.store_reading(file_text, SPAD_KEY, today)
                return file_text

            raise ValidationError("SPAD content not found for today")
        except Exception as e:
            logger.error(f"Error parsing SPAD page: {str(e)}", exc_info=True)
            raise ValidationError("Failed to parse SPAD page")

    def _write_to_file(self, content: List[str], filename: Path) -> None:
        """
        Write content to file.

        Args:
            content (List[str]): Content to write
            filename (Path): Target filename

        Raises:
            DatabaseError: If file writing fails
        """
        try:
            with open(filename, 'w', encoding="utf-8") as f:
                for line in content:
                    f.write(line)
        except IOError as e:
            logger.error(f"Error writing to file {filename}: {str(e)}", exc_info=True)
            raise DatabaseError(f"Failed to write to file {filename}")

    def _read_text_file(self, filename: Path) -> str:
        """
        Read content from file.

        Args:
            filename (Path): Source filename

        Returns:
            str: File contents

        Raises:
            DatabaseError: If file reading fails
        """
        try:
            with open(filename, 'r', encoding="utf-8") as f:
                return f.read().strip()
        except IOError as e:
            logger.error(f"Error reading file {filename}: {str(e)}", exc_info=True)
            raise DatabaseError(f"Failed to read file {filename}")

    def _extract_content(self, header: str, parsed_rows: List[str]) -> List[str]:
        """
        Extract and format content from parsed rows.

        Args:
            header (str): Header text
            parsed_rows (List[str]): List of parsed table rows

        Returns:
            List[str]: Formatted content

        Raises:
            ValidationError: If data is insufficient
        """
        if len(parsed_rows) < 6:
            raise ValidationError("Insufficient data in parsed rows")

        content = [header, '\n\n' + self._format_date(parsed_rows[0]), '\n\n' + self._format_header(parsed_rows[1]), '\n\n' + self._format_summary(parsed_rows[3]),
                           '\n\n' + self._format_reference(parsed_rows[4]), '\n\n' + parsed_rows[5].strip()]
        return content

    @staticmethod
    def _format_date(date_to_fmt: str) -> str:
        """Format date string."""
        return "_*" + date_to_fmt.strip()[0:-6] + "*_"

    @staticmethod
    def _format_header(header: str) -> str:
        """Format header string."""
        return "*" + header.strip() + "*"

    @staticmethod
    def _format_summary(summary: str) -> str:
        """Format summary string."""
        return "_" + summary.strip() + "_"

    @staticmethod
    def _format_reference(reference: str) -> str:
        """Format reference string."""
        return "*" + reference.strip() + "*"

    @staticmethod
    def _format_jft_footer(footer: str) -> str:
        """Format JFT footer string."""
        return footer.strip().replace("Just for Today:", "*Just for Today:*")

    @staticmethod
    def _format_spad_footer(footer: str) -> str:
        """Format SPAD footer string."""
        return "_" + footer.strip() + "_"

    def store_reading_to_database(self, reading_dict: Dict[str, Any], wa_id: str) -> bool:
        """
        Store a reading dictionary to the SQLite database using DatabaseService.
        
        Args:
            reading_dict (Dict[str, Any]): Dictionary containing reading data
            wa_id (str): WhatsApp ID of the recipient
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.db_service as db_service:
                reading = db_service.store_reading_with_recipient(reading_dict, wa_id)
                if reading:
                    logger.info(f"Successfully stored reading {reading.reading_type} for {reading.date} with recipient {wa_id}")
                    return True
                else:
                    logger.warning(f"Failed to store reading for recipient {wa_id}")
                    return False
        except Exception as e:
            logger.error(f"Error storing reading to database: {str(e)}", exc_info=True)
            return False

    def process_and_store_reading(self, reading_type: str, wa_id: str) -> bool:
        """
        Process a reading and store it to both shelf and SQLite databases.
        
        Args:
            reading_type (str): Type of reading ('dr', 'jft', 'spad')
            wa_id (str): WhatsApp ID of the recipient
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            today = date.strftime(date.today(), FORMAT)

            # Process the reading based on type
            if reading_type == DR_KEY:
                reading_text = self.extract_daily_reflection()
                reading_dict = dr_loader(reading_text)
            elif reading_type == JFT_KEY:
                reading_text = self.parse_jft_page()
                reading_dict = jft_loader(reading_text)
            elif reading_type == SPAD_KEY:
                reading_text = self.parse_spad_page()
                reading_dict = spad_loader(reading_text)
            else:
                logger.error(f"Unknown reading type: {reading_type}")
                return False

            # Store to SQLite database with recipient
            if reading_dict:
                success = self.store_reading_to_database(reading_dict, wa_id)
                if success:
                    logger.info(f"Successfully processed and stored {reading_type} reading for {wa_id}")
                    return True
                else:
                    logger.error(f"Failed to store {reading_type} reading to database for {wa_id}")
                    return False
            else:
                logger.error(f"Failed to parse {reading_type} reading")
                return False

        except Exception as e:
            logger.error(f"Error processing and storing reading: {str(e)}", exc_info=True)
            return False


def get_readings_db():
    """Get the readings database path from the current app context."""
    return current_app.config['READINGS_DB']


def generate_daily_reading_responses(message_body: str, wa_id: str) -> List[str]:
    """
    Generate daily reading responses.
    
    Args:
        message_body (str): Message body
        wa_id (str): WhatsApp ID
        
    Returns:
        List[str]: List of reading responses
        
    Raises:
        DatabaseError: If database operation fails
    """
    logger.info(f"Generating daily reading responses for wa_id: {wa_id}")
    today = date.strftime(date.today(), FORMAT)
    contents = []
    scraper = ReadingScraper()
    storage = ReadingStorage()

    try:
        # Process each reading type independently
        reading_processors = [(DR_KEY, scraper.extract_daily_reflection), (JFT_KEY, scraper.parse_jft_page), (SPAD_KEY, scraper.parse_spad_page)]

        for key, process_func in reading_processors:
            try:
                reading_text = process_reading(key, wa_id, today, process_func, storage)
                if reading_text:
                    contents.append(reading_text)
            except Exception as e:
                logger.error(f"Error processing {key} reading: {str(e)}", exc_info=True)
                # Continue with other readings even if one fails
                continue

        return contents
    except Exception as e:
        logger.error(f"Error generating daily reading responses: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to generate daily reading responses")


def process_reading(key: str, wa_id: str, today: str, process_func: Callable, storage: ReadingStorage) -> str:
    """
    Process reading for a specific key and date.
    
    Args:
        key (str): Reading key
        wa_id (str): WhatsApp ID
        today (str): Date string
        process_func (Callable): Function to process the reading
        storage (ReadingStorage): Storage instance
        
    Returns:
        str: Processed reading text
        
    Raises:
        DatabaseError: If database operation fails
    """
    try:
        readings = storage.retrieve_readings(key)
        today_readings = readings.get(today)
        logger.info(f"Processing reading for {key} on {today}")

        reading_text = ''
        if today_readings:
            reading_text = today_readings.get("text")

        if not reading_text:
            reading_text = process_func()

        if reading_text:
            storage.add_recipient(today, key, wa_id)

        return reading_text
    except Exception as e:
        logger.error(f"Error processing reading: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to process reading")
