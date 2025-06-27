import logging
import os
from typing import Any, Dict

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration class with default values."""
    # Flask configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

    # WhatsApp configuration
    VERIFY_TOKEN = os.getenv('VERIFY_TOKEN', '')
    ACCESS_TOKEN = os.getenv('ACCESS_TOKEN', '')
    PHONE_NUMBER_ID = os.getenv('PHONE_NUMBER_ID', '')
    VERSION = os.getenv('VERSION', 'v22.0')
    APP_ID = os.getenv('APP_ID', '')
    APP_SECRET = os.getenv('APP_SECRET', '')
    RECIPIENT_WAID = os.getenv('RECIPIENT_WAID', '')

    # Database configuration
    READINGS_DB = os.getenv('READINGS_DB', './files/readings_db')

    # Reading Service configuration
    READING_FILES_DIR = os.getenv('READING_FILES_DIR', './files')
    READING_RETRY_ATTEMPTS = int(os.getenv('READING_RETRY_ATTEMPTS', '3'))
    READING_RETRY_DELAY = int(os.getenv('READING_RETRY_DELAY', '5'))
    READING_TIMEOUT = int(os.getenv('READING_TIMEOUT', '10'))

    # Reading URLs
    JFT_URL = os.getenv('JFT_URL', 'https://www.jftna.org/jft/')
    SPAD_URL = os.getenv('SPAD_URL', 'https://www.spadna.org/')

    # Reading file paths
    DR_FILENAME = os.getenv('DR_FILENAME', 'dr.txt')
    JFT_FILENAME = os.getenv('JFT_FILENAME', 'jft.txt')
    SPAD_FILENAME = os.getenv('SPAD_FILENAME', 'spad.txt')
    REFLECTIONS_FILENAME = os.getenv('REFLECTIONS_FILENAME', 'daily_reflections.txt')

    # Cache configuration
    CACHE_TYPE = os.getenv('CACHE_TYPE', 'SimpleCache')
    CACHE_DEFAULT_TIMEOUT = int(os.getenv('CACHE_DEFAULT_TIMEOUT', '300'))
    CACHE_KEY_PREFIX = 'daily_reading_bot'

    # Logging configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = os.getenv('LOG_FILE', './logs/app.log')


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    LOG_LEVEL = 'INFO'


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    READINGS_DB = './files/test_readings_db'


# Configuration dictionary
config_by_name: Dict[str, Any] = {'development': DevelopmentConfig, 'production': ProductionConfig, 'testing': TestingConfig}


def get_config():
    """Get configuration based on environment."""
    env = os.getenv('FLASK_ENV', 'development')
    return config_by_name[env]


def configure_logging(app):
    """Configure logging for the application."""
    log_level = getattr(logging, app.config['LOG_LEVEL'])
    log_format = app.config['LOG_FORMAT']

    # Ensure logs directory exists
    log_file_path = app.config['LOG_FILE']
    log_dir = os.path.dirname(log_file_path)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # Configure file handler
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(log_format))

    # Configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format))

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Configure Flask logger
    app.logger.setLevel(log_level)
    app.logger.propagate = False  # Prevent propagation to root logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)

    app.logger.info('Logging configured successfully')
