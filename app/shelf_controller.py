import json
import logging
from flask import Blueprint, jsonify, current_app
from .utils.error_handlers import NotFoundError, DatabaseError
from .extensions import cache
from .services.shelf_reader_service import retrieve_shelf_contents, retrieve_shelf_reading, retrieve_shelf_date
import time

logger = logging.getLogger(__name__)
shelf_blueprint = Blueprint("shelf", __name__, url_prefix='/shelf')

@shelf_blueprint.route("/test-cache", methods=["GET"])
@cache.memoize(timeout=30)  # Cache for 30 seconds
def test_cache():
    """Test endpoint to verify cache functionality."""
    current_time = time.time()
    logger.info(f"Generated new timestamp: {current_time}")
    data = {
        'status': 'success',
        'timestamp': current_time,
        'message': 'This response is cached for 30 seconds. Make multiple requests to see the timestamp remain the same.'
    }
    return jsonify(data)

@shelf_blueprint.route("", methods=["GET"])
@cache.memoize(timeout=300)  # Cache for 5 minutes
def get_shelf():
    """Get all shelf contents."""
    try:
        contents = retrieve_shelf_contents()
        if not contents:
            raise NotFoundError("No shelf contents found")
        return jsonify({
            'status': 'success',
            'data': contents
        })
    except Exception as e:
        logger.error(f"Error retrieving shelf contents: {str(e)}", exc_info=True)
        raise DatabaseError("Failed to retrieve shelf contents")

@shelf_blueprint.route("/<reading>", methods=["GET"])
@cache.memoize(timeout=300)  # Cache for 5 minutes
def get_reading(reading):
    """Get specific reading from shelf."""
    try:
        content = retrieve_shelf_reading(reading)
        if not content:
            raise NotFoundError(f"Reading '{reading}' not found")
        return jsonify({
            'status': 'success',
            'data': content
        })
    except Exception as e:
        logger.error(f"Error retrieving reading {reading}: {str(e)}", exc_info=True)
        raise DatabaseError(f"Failed to retrieve reading '{reading}'")

@shelf_blueprint.route("/date/<date>", methods=["GET"])
@cache.memoize(timeout=300)  # Cache for 5 minutes
def get_date(date):
    """Get readings for specific date."""
    try:
        content = retrieve_shelf_date(date)
        if not content:
            raise NotFoundError(f"No readings found for date '{date}'")
        return jsonify({
            'status': 'success',
            'data': content
        })
    except Exception as e:
        logger.error(f"Error retrieving readings for date {date}: {str(e)}", exc_info=True)
        raise DatabaseError(f"Failed to retrieve readings for date '{date}'")
