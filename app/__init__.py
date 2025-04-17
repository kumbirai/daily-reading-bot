import flask
from flask import Flask

from app.config import load_configurations, configure_logging
from .shelf_controller import shelf_blueprint
from .whatsapp_controller import webhook_blueprint


def create_app():
    app = Flask(__name__)

    flask.json.provider.DefaultJSONProvider.sort_keys = False

    # Load configurations and logging settings
    load_configurations(app)
    configure_logging()

    # Import and register blueprints, if any
    app.register_blueprint(webhook_blueprint)
    app.register_blueprint(shelf_blueprint)

    return app
