from flask import Flask
from flask_cors import CORS

from app.config import Config, configure_logging, get_config
from app.database.init_db import init_db
from app.tasks.background_tasks import setup_background_tasks
from app.utils.error_handlers import register_error_handlers
from .extensions import cache
from .home_controller import home_blueprint
from .shelf_controller import shelf_blueprint
from .whatsapp_controller import webhook_blueprint


def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(config_class)

    # Configure logging
    configure_logging(app)

    # Initialize cache with app
    cache.init_app(app, config={'CACHE_TYPE': app.config['CACHE_TYPE'], 'CACHE_DEFAULT_TIMEOUT': app.config['CACHE_DEFAULT_TIMEOUT'], 'CACHE_KEY_PREFIX': app.config['CACHE_KEY_PREFIX']})

    # Initialize CORS
    CORS(app)

    # Initialize database tables
    with app.app_context():
        init_db()

    # Initialize background tasks
    setup_background_tasks(app)

    # Register error handlers
    register_error_handlers(app)

    # Register blueprints
    app.register_blueprint(home_blueprint)
    app.register_blueprint(webhook_blueprint)
    app.register_blueprint(shelf_blueprint)

    app.logger.info('Application initialized successfully')
    return app
