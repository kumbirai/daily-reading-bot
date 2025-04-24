import datetime
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from flask import Blueprint
from flask_restx import Api, fields

from app.services.daily_reading_service import Scrapper

logger = logging.getLogger(__name__)

# Create a blueprint for background tasks
background_tasks = Blueprint('background_tasks', __name__)
api = Api(background_tasks,
          title='Background Tasks API',
          version='1.0',
          description='API for managing background tasks'
          )

# Define models for Swagger documentation
error_model = api.model('Error', {
    'status': fields.String(description='Status of the response', example='error'),
    'message': fields.String(description='Error message', example='Task failed'),
    'code': fields.Integer(description='HTTP status code', example=500),
    'details': fields.Raw(description='Additional error details', example={
        'error_type': 'TaskError',
        'timestamp': '2025-04-24T17:21:45.227000',
        'error_message': 'Failed to execute background task',
        'suggestion': 'Please check the task configuration and try again'
    })
})

success_model = api.model('Success', {
    'status': fields.String(description='Status of the response', example='success'),
    'message': fields.String(description='Success message')
})

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
    logger.info(
        f"Background tasks scheduler started {datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()}")

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

            logger.info(
                f"Daily readings scrape completed successfully {datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()}")
    except Exception as e:
        logger.error(f"Error during daily readings scrape: {str(e)}", exc_info=True)


@background_tasks.route('/scrape', methods=['POST'])
@api.doc('trigger_scrape',
         responses={
             200: 'Scraping Completed Successfully',
             500: 'Internal Server Error'
         })
@api.marshal_with(success_model)
def trigger_scrape():
    """Manually trigger scraping of daily readings."""
    try:
        scrape_daily_readings()
        return api.marshal({
            'status': 'success',
            'message': f'Scraping completed successfully {datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()}'
        }, success_model), 200
    except Exception as e:
        logger.error(f"Error triggering manual scrape: {str(e)}", exc_info=True)
        return api.marshal({
            'status': 'error',
            'message': str(e),
            'code': 500
        }, error_model), 500
