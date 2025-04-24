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
    'details': fields.Raw(description='Additional error details', example={
        'error_type': 'NotFoundError',
        'timestamp': '2025-04-24T17:21:45.227000',
        'error_message': 'No readings found for date \'April 24\'',
        'suggestion': 'Please try a different date or check if the readings have been scraped'
    })
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

# Define namespaces
ns = api.namespace('', description='Shelf operations')

@ns.route('/test-cache')
class TestCache(Resource):
    @ns.doc('test_cache',
        responses={
            200: ('Success', success_model),
            500: ('Internal Server Error', error_model)
        })
    @ns.marshal_with(success_model)
    @cache.memoize(timeout=30)  # Cache for 30 seconds
    def get(self):
        """Test endpoint to verify cache functionality."""
        try:
            current_time = time.time()
            logger.info(f"Generated new timestamp: {current_time}")
            return {
                'status': 'success',
                'data': {
                    'timestamp': current_time,
                    'message': 'This response is cached for 30 seconds. Make multiple requests to see the timestamp remain the same.'
                }
            }
        except Exception as e:
            logger.error(f"Error in test-cache endpoint: {str(e)}", exc_info=True)
            return api.marshal(
                {
                    'status': 'error',
                    'message': 'An unexpected error occurred',
                    'code': 500,
                    'details': {
                        'error_type': type(e).__name__,
                        'timestamp': datetime.now().isoformat(),
                        'error_message': str(e),
                        'suggestion': 'Please try again later or contact support if the issue persists'
                    }
                }, error_model), 500

@ns.route('')
class Shelf(Resource):
    @ns.doc('get_shelf',
        responses={
            200: ('Success', success_model),
            500: ('Internal Server Error', error_model)
        })
    @ns.marshal_with(success_model)
    @cache.memoize(timeout=300)  # Cache for 5 minutes
    def get(self):
        """Get all shelf contents."""
        try:
            contents = retrieve_shelf_contents()
            if not contents:
                return {
                    'status': 'success',
                    'data': {},
                    'message': 'No shelf contents found'
                }
            return {
                'status': 'success',
                'data': contents
            }
        except DatabaseError as e:
            logger.error(f"Database error retrieving shelf contents: {str(e)}", exc_info=True)
            return api.marshal({
                'status': 'error',
                'message': 'An unexpected error occurred while retrieving shelf contents',
                'code': 500,
                'details': {
                    'error_type': 'DatabaseError',
                    'timestamp': datetime.now().isoformat(),
                    'error_message': str(e),
                    'suggestion': 'Please try again later or contact support if the issue persists'
                }
            }, error_model), 500
        except Exception as e:
            logger.error(f"Unexpected error retrieving shelf contents: {str(e)}", exc_info=True)
            return api.marshal({
                'status': 'error',
                'message': 'An unexpected error occurred while retrieving shelf contents',
                'code': 500,
                'details': {
                    'error_type': type(e).__name__,
                    'timestamp': datetime.now().isoformat(),
                    'error_message': str(e),
                    'suggestion': 'Please try again later or contact support if the issue persists'
                }
            }, error_model), 500

@ns.route('/<reading>')
@ns.param('reading', 'Reading type (dr, jft, spad)')
class Reading(Resource):
    @ns.doc('get_reading',
        responses={
            200: ('Success', success_model),
            404: ('Reading Not Found', error_model),
            500: ('Internal Server Error', error_model)
        })
    @ns.marshal_with(success_model)
    @cache.memoize(timeout=300)  # Cache for 5 minutes
    def get(self, reading):
        """Get specific reading from shelf."""
        try:
            content = retrieve_shelf_reading(reading)
            return {
                'status': 'success',
                'data': content,
                'message': f'Successfully retrieved reading {reading}'
            }
        except NotFoundError as e:
            error_response = {
                'status': 'error',
                'message': f"Reading '{reading}' not found",
                'code': 404,
                'details': {
                    'error_type': 'NotFoundError',
                    'timestamp': datetime.now().isoformat(),
                    'error_message': str(e),
                    'suggestion': 'Please check your request and try again. Available reading types are: [dr, jft, spad]'
                }
            }
            return error_response, 404
        except Exception as e:
            error_response = {
                'status': 'error',
                'message': f"An unexpected error occurred while retrieving reading '{reading}'",
                'code': 500,
                'details': {
                    'error_type': type(e).__name__,
                    'timestamp': datetime.now().isoformat(),
                    'error_message': str(e),
                    'suggestion': 'Please try again later or contact support if the issue persists.'
                }
            }
            return error_response, 500

@ns.route('/date/<date>')
@ns.param('date', 'Date in format "Month DD" (e.g., "April 24")')
class DateReadings(Resource):
    @ns.doc('get_date',
        responses={
            200: ('Success', success_model),
            400: ('Invalid Date Format', error_model),
            404: ('No Readings Found', error_model),
            500: ('Internal Server Error', error_model)
        })
    @ns.marshal_with(success_model)
    @cache.memoize(timeout=300)  # Cache for 5 minutes
    def get(self, date):
        """Get readings for specific date."""
        try:
            content = retrieve_shelf_date(date)
            return {
                'status': 'success',
                'data': content,
                'message': f'Successfully retrieved readings for date {date}'
            }
        except ValidationError as e:
            error_response = {
                'status': 'error',
                'message': str(e),
                'code': 400,
                'details': {
                    'error_type': 'ValidationError',
                    'timestamp': datetime.now().isoformat(),
                    'error_message': str(e),
                    'suggestion': 'Please use the format "Month DD" (e.g., "April 24")'
                }
            }
            return error_response, 400
        except NotFoundError as e:
            error_response = {
                'status': 'error',
                'message': f'No readings found for date {date}',
                'code': 404,
                'details': {
                    'error_type': 'NotFoundError',
                    'timestamp': datetime.now().isoformat(),
                    'error_message': str(e),
                    'suggestion': 'Please try a different date or check if the readings have been scraped'
                }
            }
            return error_response, 404
        except Exception as e:
            error_response = {
                'status': 'error',
                'message': f"An unexpected error occurred while retrieving readings for date '{date}'",
                'code': 500,
                'details': {
                    'error_type': type(e).__name__,
                    'timestamp': datetime.now().isoformat(),
                    'error_message': str(e),
                    'suggestion': 'Please try again later or contact support if the issue persists'
                }
            }
            return error_response, 500

# Register error handler for Flask-RESTX errors
@api.errorhandler
def handle_api_error(error):
    """Handle Flask-RESTX errors."""
    logger.error(f"API Error: {error.description}", exc_info=True)
    return {
        'status': 'error',
        'message': error.description,
        'code': error.code,
        'details': getattr(error, 'details', {
            'error_type': type(error).__name__,
            'timestamp': datetime.now().isoformat(),
            'error_message': str(error),
            'suggestion': 'Please check your request and try again'
        })
    }, error.code
