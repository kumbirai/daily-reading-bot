from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import logging
from app.services.daily_reading_service import Scrapper
from flask import Blueprint

logger = logging.getLogger(__name__)

# Create a blueprint for background tasks
background_tasks = Blueprint('background_tasks', __name__)

def setup_background_tasks(app):
    """Setup background tasks for the application."""
    scheduler = BackgroundScheduler()
    
    # Schedule daily scraping at 03:00 AM
    scheduler.add_job(
        func=scrape_daily_readings,
        trigger=CronTrigger(hour=3, minute=0),
        id='daily_scraping',
        name='Scrape daily readings',
        replace_existing=True
    )
    
    # Schedule scraping every 3 hours
    scheduler.add_job(
        func=scrape_daily_readings,
        trigger=IntervalTrigger(hours=3),
        id='periodic_scraping',
        name='Periodic scrape every 3 hours',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Background tasks scheduler started")
    
    # Store scheduler in app context
    app.scheduler = scheduler
    
    # Register the blueprint
    app.register_blueprint(background_tasks, url_prefix='/tasks')

def scrape_daily_readings():
    """Scrape all daily readings and store them in the database."""
    try:
        logger.info("Starting daily readings scrape")
        scrapper = Scrapper()
        
        # Scrape each reading type
        scrapper.extract_daily_reflection()
        scrapper.parse_jft_page()
        scrapper.parse_spad_page()
        
        logger.info("Daily readings scrape completed successfully")
    except Exception as e:
        logger.error(f"Error during daily readings scrape: {str(e)}", exc_info=True)

@background_tasks.route('/scrape', methods=['POST'])
def trigger_scrape():
    """Manually trigger scraping of daily readings."""
    try:
        scrape_daily_readings()
        return {'status': 'success', 'message': 'Scraping completed successfully'}, 200
    except Exception as e:
        logger.error(f"Error triggering manual scrape: {str(e)}", exc_info=True)
        return {'status': 'error', 'message': str(e)}, 500 