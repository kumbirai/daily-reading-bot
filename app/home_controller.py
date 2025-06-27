import logging
from datetime import date

from flask import Blueprint, render_template

from .services.database_service import DatabaseService

logger = logging.getLogger(__name__)
home_blueprint = Blueprint("home", __name__)


def get_todays_date():
    """Get today's date in the format used by the readings database."""
    return date.strftime(date.today(), '%B %d')


def get_todays_readings():
    """Get today's readings for all three types from the database."""
    try:
        today = get_todays_date()

        with DatabaseService() as db_service:
            # Get readings for each type
            daily_reading = db_service.get_reading_by_date_and_type(today, 'dr')
            just_for_today = db_service.get_reading_by_date_and_type(today, 'jft')
            spiritual_principal = db_service.get_reading_by_date_and_type(today, 'spad')

        return {'daily_reading': daily_reading, 'just_for_today': just_for_today, 'spiritual_principal': spiritual_principal, 'date': today}
    except Exception as e:
        logger.error(f"Error retrieving today's readings: {str(e)}", exc_info=True)
        return {'daily_reading': None, 'just_for_today': None, 'spiritual_principal': None, 'date': get_todays_date()}


@home_blueprint.route("/", methods=["GET"])
def home():
    """Home page displaying today's readings."""
    readings = get_todays_readings()
    return render_template('home.html', readings=readings)
