import json
import logging
from flask import Blueprint, jsonify, current_app
from .utils.error_handlers import NotFoundError, DatabaseError, ValidationError
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
            return jsonify({
                'status': 'success',
                'data': {},
                'message': 'No shelf contents found'
            }), 200
        return jsonify({
            'status': 'success',
            'data': contents
        })
    except DatabaseError as e:
        logger.error(f"Database error retrieving shelf contents: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'An unexpected error occurred while retrieving shelf contents',
            'code': 500,
            'details': {}
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error retrieving shelf contents: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'An unexpected error occurred while retrieving shelf contents',
            'code': 500,
            'details': {}
        }), 500

@shelf_blueprint.route("/<reading>", methods=["GET"])
@cache.memoize(timeout=300)  # Cache for 5 minutes
def get_reading(reading):
    """Get specific reading from shelf."""
    try:
        content = retrieve_shelf_reading(reading)
        return jsonify({
            'status': 'success',
            'data': content
        })
    except NotFoundError as e:
        logger.warning(f"Reading not found: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Reading '{reading}' not found",
            'code': 404,
            'details': {}
        }), 404
    except DatabaseError as e:
        logger.error(f"Database error retrieving reading {reading}: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f"An unexpected error occurred while retrieving reading '{reading}'",
            'code': 500,
            'details': {}
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error retrieving reading {reading}: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f"An unexpected error occurred while retrieving reading '{reading}'",
            'code': 500,
            'details': {}
        }), 500

@shelf_blueprint.route("/date/<date>", methods=["GET"])
@cache.memoize(timeout=300)  # Cache for 5 minutes
def get_date(date):
    """Get readings for specific date."""
    try:
        content = retrieve_shelf_date(date)
        return jsonify({
            'status': 'success',
            'data': content
        })
    except ValidationError as e:
        logger.warning(f"Invalid date format: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Invalid date format',
            'code': 400,
            'details': {}
        }), 400
    except NotFoundError as e:
        logger.warning(f"No readings found for date {date}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"No readings found for date '{date}'",
            'code': 404,
            'details': {}
        }), 404
    except DatabaseError as e:
        logger.error(f"Database error retrieving readings for date {date}: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f"An unexpected error occurred while retrieving readings for date '{date}'",
            'code': 500,
            'details': {}
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error retrieving readings for date {date}: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f"An unexpected error occurred while retrieving readings for date '{date}'",
            'code': 500,
            'details': {}
        }), 500
