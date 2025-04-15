import datetime
import logging
import shelve
from datetime import date
from typing import Any

import requests
from bs4 import BeautifulSoup

FORMAT = '%B %d'
READINGS_DB = "./readings_db"
DR_KEY = 'dr'
JFT_KEY = 'jft'
SPAD_KEY = 'spad'


def parse_table(url: Any) -> list[str]:
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    rows = soup.find_all('tr')
    data = []
    for row in rows:
        td = row.find('td')
        for br_tag in td.find_all('br'):
            new_tag = soup.new_tag("b")
            new_tag.string = '\n'
            br_tag.replace_with(new_tag)
        text = td.text
        data.append(text)
    return data


def extract_content(header, parsed_rows):
    logging.info(parsed_rows)
    content = []
    content.append(header)
    content.append('\n\n' + format_date(parsed_rows[0]))
    content.append('\n\n' + format_header(parsed_rows[1]))
    content.append('\n\n' + format_summary(parsed_rows[3]))
    content.append('\n\n' + format_reference(parsed_rows[4]))
    content.append('\n\n' + parsed_rows[5].strip())
    return content


def format_date(date_to_fmt: str) -> str:
    return "_*" + date_to_fmt.strip()[0:-6] + "*_"


def format_header(header: str) -> str:
    return "*" + header.strip() + "*"


def format_summary(summary: str) -> str:
    return "_" + summary.strip() + "_"


def format_reference(reference: str) -> str:
    return "*" + reference.strip() + "*"


def format_jft_footer(footer: str) -> str:
    return footer.strip().replace("Just for Today:", "*Just for Today:*")


def format_spad_footer(footer: str) -> str:
    return "_" + footer.strip() + "_"


def write_list_to_file(content: list[str], filename: str) -> None:
    with open(filename, 'w') as f:
        for line in content:
            f.write(line)


def read_text_file(filename: str) -> str:
    with open(filename, 'r') as f:
        content = f.read()
        return content.strip()


def store_reading(file_text, key, today):
    with shelve.open(READINGS_DB, writeback=True) as readings_shelf:
        try:
            readings = readings_shelf.get(key, {})
            readings[today] = {
                "text": file_text,
                "extract_date": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "recipients": []
            }
            readings_shelf[key] = readings
        finally:
            readings_shelf.close()


def retrieve_readings(key) -> dict[Any, Any]:
    with shelve.open(READINGS_DB) as readings_shelf:
        return readings_shelf.get(key, {})


class Scrapper:
    dr_filename = './dr.txt'
    jft_filename = './jft.txt'
    spad_filename = './spad.txt'
    reflections_filename = './daily_reflections.txt'

    def extract_daily_reflection(self) -> str:
        with open(self.reflections_filename, 'rt') as reflections:
            contents = reflections.read()

        today = date.strftime(date.today(), FORMAT)

        start = contents.find(f"_*{date.strftime(date.today(), '%B %-d')}*_")
        end = contents.find("_*", start + 1)

        today_readings = contents[start:end].strip()

        with open(self.dr_filename, 'w') as f:
            f.write(today_readings)

        store_reading(today_readings, DR_KEY, today)
        return today_readings

    def parse_jft_page(self) -> str:
        try:
            jft_site = 'https://www.jftna.org/jft/'
            jft_rows = parse_table(jft_site)
            content = extract_content('❇️ *Just For Today* ❇️', jft_rows)
            content.append('\n\n' + format_jft_footer(jft_rows[6]))

            write_list_to_file(content, self.jft_filename)

            file_text = read_text_file(self.jft_filename)
            today = date.strftime(date.today(), FORMAT)
            if file_text.find(today) != -1:
                store_reading(file_text, JFT_KEY, today)
                return file_text
        except Exception as e:
            logging.error(e)
        return ''

    def parse_spad_page(self) -> str:
        try:
            spad_site = 'https://www.spadna.org/'
            spad_rows = parse_table(spad_site)
            content = extract_content('🔷 *Spiritual Principle A Day* 🔷', spad_rows)
            content.append('\n\n' + spad_rows[6].strip())
            content.append('\n\n' + format_spad_footer(spad_rows[7]))

            write_list_to_file(content, self.spad_filename)

            file_text = read_text_file(self.spad_filename)
            today = date.strftime(date.today(), FORMAT)
            if file_text.find(today) != -1:
                store_reading(file_text, SPAD_KEY, today)
                return file_text
        except Exception as e:
            logging.error(e)
        return ''


def generate_daily_reading_responses(message_body, wa_id) -> list[str]:
    logging.info(f"Generating daily reading responses. Message body: {message_body}")
    today = date.strftime(date.today(), FORMAT)
    contents = []

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


def process_reading(key, wa_id, today):
    readings = retrieve_readings(key)
    # logging.info(f"readings: {readings}")
    today_readings = readings.get(today)
    logging.info(f"Today readings for {key}:\n{today_readings}")
    reading_text = ''
    if today_readings:
        reading_text = today_readings.get("text")
    if not reading_text:
        if key == DR_KEY:
            reading_text = Scrapper.extract_daily_reflection(Scrapper())
        if key == JFT_KEY:
            reading_text = Scrapper.parse_jft_page(Scrapper())
        if key == SPAD_KEY:
            reading_text = Scrapper.parse_spad_page(Scrapper())

    if reading_text:
        wa_id_data = get_wa_id_data(today, key, wa_id)
        if not wa_id_data:
            with shelve.open(READINGS_DB, writeback=True) as readings_shelf:
                try:
                    readings = readings_shelf.get(key)
                    recipient = {
                        "wa_id": wa_id,
                        "sent": datetime.datetime.now(datetime.timezone.utc).isoformat()
                    }
                    recipients = list(readings.get(today).get("recipients"))
                    recipients.append(recipient.copy())
                    readings.get(today)["recipients"] = recipients
                    readings_shelf[key] = readings
                    logging.info(f"recipients: {readings.get(today).get("recipients")}")
                finally:
                    readings_shelf.close()
        else:
            logging.info(f"wa_id {wa_id_data.get("wa_id")} is already processed on {wa_id_data.get("sent")}.")
            reading_text = ''

    return reading_text


def get_wa_id_data(today, key, wa_id) -> dict[Any, Any]:
    with shelve.open(READINGS_DB) as readings_shelf:
        readings = readings_shelf.get(key)
        recipients = list(readings.get(today).get("recipients"))
        return next((item for item in recipients if item["wa_id"] == wa_id), {})
