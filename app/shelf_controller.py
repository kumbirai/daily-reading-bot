import logging
import time
from datetime import datetime

from flask import Blueprint, jsonify
from flask_restx import Api, Resource, fields

from .extensions import cache
from .services.shelf_reader_service import retrieve_shelf_contents, retrieve_shelf_reading, retrieve_shelf_date
from .utils.error_handlers import NotFoundError, DatabaseError, ValidationError

logger = logging.getLogger(__name__)
shelf_blueprint = Blueprint("shelf", __name__, url_prefix='/shelf')
api = Api(shelf_blueprint, 
    title='Daily Reading Bot API',
    version='1.0',
    description='API for retrieving daily readings and managing the reading shelf'
)

# Define models for Swagger documentation
error_model = api.model('Error', {
    'status': fields.String(description='Status of the response', example='error'),
    'message': fields.String(description='Error message', example='Reading not found'),
    'code': fields.Integer(description='HTTP status code', example=404),
    'details': fields.Raw(description='Additional error details')
})

success_model = api.model('Success', {
    'status': fields.String(description='Status of the response', example='success'),
    'data': fields.Raw(description='Response data'),
    'message': fields.String(description='Success message', required=False)
})

reading_model = api.model('Reading', {
    'text': fields.String(description='Reading text'),
    'extract_date': fields.String(description='Date when the reading was extracted'),
    'recipients': fields.List(fields.Raw, description='List of recipients who received this reading')
})

date_readings_model = api.model('DateReadings', {
    'dr': fields.Nested(reading_model, description='Daily Reflection reading'),
    'jft': fields.Nested(reading_model, description='Just For Today reading'),
    'spad': fields.Nested(reading_model, description='Spiritual Principle A Day reading')
})

@shelf_blueprint.route("/test-cache", methods=["GET"])
@cache.memoize(timeout=30)  # Cache for 30 seconds
@api.doc('test_cache',
    responses={
        200: 'Success',
        500: 'Internal Server Error'
    })
@api.marshal_with(success_model)
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
@api.doc('get_shelf',
    responses={
        200: 'Success',
        500: 'Internal Server Error'
    })
@api.marshal_with(success_model)
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
            'details': {
                'error_type': 'DatabaseError',
                'timestamp': datetime.now().isoformat(),
                'error_message': str(e),
                'suggestion': 'Please try again later or contact support if the issue persists'
            }
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error retrieving shelf contents: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'An unexpected error occurred while retrieving shelf contents',
            'code': 500,
            'details': {
                'error_type': type(e).__name__,
                'timestamp': datetime.now().isoformat(),
                'error_message': str(e),
                'suggestion': 'Please try again later or contact support if the issue persists'
            }
        }), 500


@shelf_blueprint.route("/<reading>", methods=["GET"])
@cache.memoize(timeout=300)  # Cache for 5 minutes
@api.doc('get_reading',
    params={'reading': 'Reading type (dr, jft, spad)'},
    responses={
        200: 'Success',
        404: 'Reading Not Found',
        500: 'Internal Server Error'
    })
@api.marshal_with(success_model)
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
            'details': {
                'error_type': 'NotFoundError',
                'timestamp': datetime.now().isoformat(),
                'requested_reading': reading,
                'available_readings': ['dr', 'jft', 'spad'],
                'suggestion': 'Please check the reading type and try again'
            }
        }), 404
    except DatabaseError as e:
        logger.error(f"Database error retrieving reading {reading}: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f"An unexpected error occurred while retrieving reading '{reading}'",
            'code': 500,
            'details': {
                'error_type': 'DatabaseError',
                'timestamp': datetime.now().isoformat(),
                'requested_reading': reading,
                'error_message': str(e),
                'suggestion': 'Please try again later or contact support if the issue persists'
            }
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error retrieving reading {reading}: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f"An unexpected error occurred while retrieving reading '{reading}'",
            'code': 500,
            'details': {
                'error_type': type(e).__name__,
                'timestamp': datetime.now().isoformat(),
                'requested_reading': reading,
                'error_message': str(e),
                'suggestion': 'Please try again later or contact support if the issue persists'
            }
        }), 500


@shelf_blueprint.route("/date/<date>", methods=["GET"])
@cache.memoize(timeout=300)  # Cache for 5 minutes
@api.doc('get_date',
    params={'date': 'Date in format "Month DD" (e.g., "April 24")'},
    responses={
        200: 'Success',
        400: 'Invalid Date Format',
        404: 'No Readings Found',
        500: 'Internal Server Error'
    })
@api.marshal_with(success_model)
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
            'details': {
                'error_type': 'ValidationError',
                'timestamp': datetime.now().isoformat(),
                'provided_date': date,
                'expected_format': 'Month DD (e.g., "April 24")',
                'suggestion': 'Please provide the date in the correct format'
            }
        }), 400
    except NotFoundError as e:
        logger.warning(f"No readings found for date {date}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"No readings found for date '{date}'",
            'code': 404,
            'details': {
                'error_type': 'NotFoundError',
                'timestamp': datetime.now().isoformat(),
                'requested_date': date,
                'suggestion': 'Please check the date or try a different date'
            }
        }), 404
    except DatabaseError as e:
        logger.error(f"Database error retrieving readings for date {date}: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f"An unexpected error occurred while retrieving readings for date '{date}'",
            'code': 500,
            'details': {
                'error_type': 'DatabaseError',
                'timestamp': datetime.now().isoformat(),
                'requested_date': date,
                'error_message': str(e),
                'suggestion': 'Please try again later or contact support if the issue persists'
            }
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error retrieving readings for date {date}: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f"An unexpected error occurred while retrieving readings for date '{date}'",
            'code': 500,
            'details': {
                'error_type': type(e).__name__,
                'timestamp': datetime.now().isoformat(),
                'requested_date': date,
                'error_message': str(e),
                'suggestion': 'Please try again later or contact support if the issue persists'
            }
        }), 500
