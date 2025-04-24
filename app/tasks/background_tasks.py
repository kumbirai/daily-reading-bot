import datetime
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from flask import Blueprint

from app.services.daily_reading_service import Scrapper

logger = logging.getLogger(__name__)

# Create a blueprint for background tasks
background_tasks = Blueprint('background_tasks', __name__)

# Store the Flask app instance
_app = None


def setup_background_tasks(app):
    """Setup background tasks for the application."""
    global _app
    _app = app

    scheduler = BackgroundScheduler()

    # Schedule scraping every 3 hours
    scheduler.add_job(
        func=scrape_daily_readings,
        trigger=IntervalTrigger(hours=3),
        id='periodic_scraping',
        name='Periodic scrape every 3 hours',
        replace_existing=True
    )

    scheduler.start()
    logger.info(f"Background tasks scheduler started {datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()}")

    # Store scheduler in app context
    app.scheduler = scheduler

    # Register the blueprint
    app.register_blueprint(background_tasks, url_prefix='/tasks')


def scrape_daily_readings():
    """Scrape all daily readings and store them in the database."""
    try:
        logger.info("Starting daily readings scrape")
        # Use the stored app instance for context
        with _app.app_context():
            scrapper = Scrapper()

            # Scrape each reading type
            scrapper.extract_daily_reflection()
            scrapper.parse_jft_page()
            scrapper.parse_spad_page()

            logger.info(f"Daily readings scrape completed successfully {datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()}")
    except Exception as e:
        logger.error(f"Error during daily readings scrape: {str(e)}", exc_info=True)


@background_tasks.route('/scrape', methods=['POST'])
def trigger_scrape():
    """Manually trigger scraping of daily readings."""
    try:
        scrape_daily_readings()
        return {'status': 'success', 'message': f'Scraping completed successfully {datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()}'}, 200
    except Exception as e:
        logger.error(f"Error triggering manual scrape: {str(e)}", exc_info=True)
        return {'status': 'error', 'message': str(e)}, 500
