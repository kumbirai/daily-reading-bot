import json
import logging
import shelve
from sys import excepthook

from app.services.daily_reading_service import READINGS_DB


def retrieve_shelf_contents():
    with shelve.open(READINGS_DB) as readings:
        try:
            readings_dict = dict(readings)
            logging.info(f"\n{json.dumps(readings_dict, indent=2)}")
            return readings_dict
        finally:
            readings.close()


def retrieve_shelf_reading(reading):
    with shelve.open(READINGS_DB) as readings:
        try:
            data = {}
            try:
                this_reading = readings[reading]
                if this_reading:
                    reading_content = dict(this_reading).copy()
                    data[reading] = reading_content
                    logging.info(f"\n{json.dumps(data, indent=2)}")
            except KeyError:
                logging.error(f"Error encountered:\n{KeyError}: {reading}")
            return data
        finally:
            readings.close()


def retrieve_shelf_date(date):
    with shelve.open(READINGS_DB) as readings:
        try:
            readings_dict = dict(readings)
            data = {}
            for key, value in readings_dict.items():
                date_value = dict(value.get(date, {})).copy()
                if date_value:
                    data[key] = {date: date_value}
                    logging.info(f"\n{json.dumps(data, indent=2)}")
            return data
        finally:
            readings.close()


if __name__ == "__main__":
    logging.info(retrieve_shelf_contents())
    logging.info(retrieve_shelf_reading('dr'))
    logging.info(retrieve_shelf_date('April 16'))
