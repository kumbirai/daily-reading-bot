import datetime
import logging
import shelve
from datetime import date
from typing import Any, List, Dict

import requests
from bs4 import BeautifulSoup
from flask import current_app

from ..extensions import cache
from ..utils.error_handlers import DatabaseError, ValidationError

logger = logging.getLogger(__name__)

FORMAT = '%B %d'
DR_KEY = 'dr'
JFT_KEY = 'jft'
SPAD_KEY = 'spad'


def get_readings_db():
    """Get the readings database path from the current app context."""
    return current_app.config['READINGS_DB']


def parse_table(url: str) -> List[str]:
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
        response = requests.get(url, timeout=10)
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
    except requests.RequestException as e:
        logger.error(f"Error fetching or parsing table from {url}: {str(e)}", exc_info=True)
        raise ValidationError(f"Failed to fetch or parse table from {url}")


def extract_content(header: str, parsed_rows: List[str]) -> List[str]:
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

    content = [
        header,
        '\n\n' + format_date(parsed_rows[0]),
        '\n\n' + format_header(parsed_rows[1]),
        '\n\n' + format_summary(parsed_rows[3]),
        '\n\n' + format_reference(parsed_rows[4]),
        '\n\n' + parsed_rows[5].strip()
    ]
    return content


def format_date(date_to_fmt: str) -> str:
    """Format date string."""
    return "_*" + date_to_fmt.strip()[0:-6] + "*_"


def format_header(header: str) -> str:
    """Format header string."""
    return "*" + header.strip() + "*"


def format_summary(summary: str) -> str:
    """Format summary string."""
    return "_" + summary.strip() + "_"


def format_reference(reference: str) -> str:
    """Format reference string."""
    return "*" + reference.strip() + "*"


def format_jft_footer(footer: str) -> str:
    """Format JFT footer string."""
    return footer.strip().replace("Just for Today:", "*Just for Today:*")


def format_spad_footer(footer: str) -> str:
    """Format SPAD footer string."""
    return "_" + footer.strip() + "_"


def write_list_to_file(content: List[str], filename: str) -> None:
    """
    Write content to file.
    
    Args:
        content (List[str]): Content to write
        filename (str): Target filename
        
    Raises:
        DatabaseError: If file writing fails
    """
    try:
        with open(filename, 'w') as f:
            for line in content:
                f.write(line)
    except IOError as e:
        logger.error(f"Error writing to file {filename}: {str(e)}", exc_info=True)
        raise DatabaseError(f"Failed to write to file {filename}")


def read_text_file(filename: str) -> str:
    """
    Read content from file.
    
    Args:
        filename (str): Source filename
        
    Returns:
        str: File contents
        
    Raises:
        DatabaseError: If file reading fails
    """
    try:
        with open(filename, 'r') as f:
            return f.read().strip()
    except IOError as e:
        logger.error(f"Error reading file {filename}: {str(e)}", exc_info=True)
        raise DatabaseError(f"Failed to read file {filename}")


def store_reading(file_text: str, key: str, today: str) -> None:
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
        with shelve.open(get_readings_db(), writeback=True) as readings_shelf:
            readings = readings_shelf.get(key, {})
            readings[today] = {
                "text": file_text,
                "extract_date": datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(),
                "recipients": []
            }
            readings_shelf[key] = readings
    except Exception as e:
        logger.error(f"Error storing reading in database: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to store reading in database")


@cache.memoize(timeout=3600)  # Cache for 1 hour
def retrieve_readings(key: str) -> Dict[str, Any]:
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
        with shelve.open(get_readings_db()) as readings_shelf:
            return readings_shelf.get(key, {})
    except Exception as e:
        logger.error(f"Error retrieving readings from database: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to retrieve readings from database")


class Scrapper:
    """Class for scraping daily readings from various sources."""

    def __init__(self):
        self.dr_filename = './files/dr.txt'
        self.jft_filename = './files/jft.txt'
        self.spad_filename = './files/spad.txt'
        self.reflections_filename = './files/daily_reflections.txt'

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
            with open(self.reflections_filename, 'rt') as reflections:
                contents = reflections.read()

            today = date.strftime(date.today(), FORMAT)
            start = contents.find(f"_*{date.strftime(date.today(), '%B %-d')}*_")

            if start == -1:
                raise ValidationError("Daily reflection not found for today")

            end = contents.find("_*", start + 1)
            if end == -1:
                end = len(contents)

            today_readings = contents[start:end].strip()

            write_list_to_file([today_readings], self.dr_filename)
            store_reading(today_readings, DR_KEY, today)

            return today_readings
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error extracting daily reflection: {str(e)}", exc_info=True)
            raise DatabaseError("Failed to extract daily reflection")

    def parse_jft_page(self) -> str:
        """
        Parse Just for Today page.
        
        Returns:
            str: Parsed JFT content
            
        Raises:
            ValidationError: If parsing fails
        """
        try:
            jft_site = 'https://www.jftna.org/jft/'
            jft_rows = parse_table(jft_site)

            if not jft_rows:
                raise ValidationError("No content found on JFT page")

            content = extract_content('❇️ *Just For Today* ❇️', jft_rows)
            content.append('\n\n' + format_jft_footer(jft_rows[6]))

            write_list_to_file(content, self.jft_filename)

            file_text = read_text_file(self.jft_filename)
            today = date.strftime(date.today(), FORMAT)

            if file_text.find(today) != -1:
                store_reading(file_text, JFT_KEY, today)
                return file_text

            raise ValidationError("JFT content not found for today")
        except Exception as e:
            logger.error(f"Error parsing JFT page: {str(e)}", exc_info=True)
            raise ValidationError("Failed to parse JFT page")

    def parse_spad_page(self) -> str:
        """
        Parse Spiritual Principle A Day page.
        
        Returns:
            str: Parsed SPAD content
            
        Raises:
            ValidationError: If parsing fails
        """
        try:
            spad_site = 'https://www.spadna.org/'
            spad_rows = parse_table(spad_site)

            if not spad_rows:
                raise ValidationError("No content found on SPAD page")

            content = extract_content('🔷 *Spiritual Principle A Day* 🔷', spad_rows)
            content.append('\n\n' + spad_rows[6].strip())
            content.append('\n\n' + format_spad_footer(spad_rows[7]))

            write_list_to_file(content, self.spad_filename)

            file_text = read_text_file(self.spad_filename)
            today = date.strftime(date.today(), FORMAT)

            if file_text.find(today) != -1:
                store_reading(file_text, SPAD_KEY, today)
                return file_text

            raise ValidationError("SPAD content not found for today")
        except Exception as e:
            logger.error(f"Error parsing SPAD page: {str(e)}", exc_info=True)
            raise ValidationError("Failed to parse SPAD page")


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

    try:
        reading_text = process_reading(DR_KEY, wa_id, today)
        if reading_text:
            contents.append(reading_text)

        reading_text = process_reading(JFT_KEY, wa_id, today)
        if reading_text:
            contents.append(reading_text)

        reading_text = process_reading(SPAD_KEY, wa_id, today)
        if reading_text:
            contents.append(reading_text)

        return contents
    except Exception as e:
        logger.error(f"Error generating daily reading responses: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to generate daily reading responses")


def process_reading(key: str, wa_id: str, today: str) -> str:
    """
    Process reading for a specific key and date.
    
    Args:
        key (str): Reading key
        wa_id (str): WhatsApp ID
        today (str): Date string
        
    Returns:
        str: Processed reading text
        
    Raises:
        DatabaseError: If database operation fails
    """
    try:
        readings = retrieve_readings(key)
        today_readings = readings.get(today)
        logger.info(f"Processing reading for {key} on {today}")

        reading_text = ''
        if today_readings:
            reading_text = today_readings.get("text")

        if not reading_text:
            scrapper = Scrapper()
            if key == DR_KEY:
                reading_text = scrapper.extract_daily_reflection()
            elif key == JFT_KEY:
                reading_text = scrapper.parse_jft_page()
            elif key == SPAD_KEY:
                reading_text = scrapper.parse_spad_page()

        if reading_text:
            wa_id_data = get_wa_id_data(today, key, wa_id)
            if not wa_id_data:
                with shelve.open(get_readings_db(), writeback=True) as readings_shelf:
                    readings = readings_shelf.get(key)
                    recipient = {
                        "wa_id": wa_id,
                        "sent": datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()
                    }
                    recipients = list(readings.get(today).get("recipients"))
                    recipients.append(recipient.copy())
                    readings.get(today)["recipients"] = recipients
                    readings_shelf[key] = readings
                    logger.info(f"Added recipient {wa_id} to {key} reading for {today}")
            else:
                logger.info(f"Recipient {wa_id} already received {key} reading for {today}")
                reading_text = ''

        return reading_text
    except Exception as e:
        logger.error(f"Error processing reading: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to process reading")


def get_wa_id_data(today: str, key: str, wa_id: str) -> Dict[str, Any]:
    """
    Get WhatsApp ID data for a specific reading.
    
    Args:
        today (str): Date string
        key (str): Reading key
        wa_id (str): WhatsApp ID
        
    Returns:
        Dict[str, Any]: WhatsApp ID data
        
    Raises:
        DatabaseError: If database operation fails
    """
    try:
        with shelve.open(get_readings_db()) as readings_shelf:
            readings = readings_shelf.get(key)
            if not readings or today not in readings:
                return {}
            recipients = list(readings.get(today).get("recipients", []))
            return next((item for item in recipients if item["wa_id"] == wa_id), {})
    except Exception as e:
        logger.error(f"Error getting WhatsApp ID data: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to get WhatsApp ID data")
