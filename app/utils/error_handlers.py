import logging
from datetime import datetime
from typing import Any, Dict, Optional

from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base class for API errors."""

    def __init__(self, message: str, status_code: int = 500, payload: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format."""
        rv = {'status': 'error', 'message': self.message, 'code': self.status_code, 'details': {'error_type': type(self).__name__, 'timestamp': datetime.now().isoformat(), 'error_message': str(self),
            'suggestion': self.payload.get('suggestion', 'Please try again later or contact support if the issue persists')}}
        # Add any additional payload fields to details
        for key, value in self.payload.items():
            if key != 'suggestion':
                rv['details'][key] = value
        return rv


class ValidationError(APIError):
    """Raised when input validation fails."""

    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=400, payload=payload)


class NotFoundError(APIError):
    """Raised when a resource is not found."""

    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=404, payload=payload)


class DatabaseError(APIError):
    """Raised when a database operation fails."""

    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, payload=payload)


def register_error_handlers(app):
    """Register error handlers for the application."""

    @app.errorhandler(APIError)
    def handle_api_error(error: APIError):
        """Handle API errors."""
        logger.error(f"API Error: {error.message}", exc_info=True)
        return error.to_dict(), error.status_code

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        """Handle HTTP errors."""
        logger.error(f"HTTP Error: {error.description}", exc_info=True)
        return {'status': 'error', 'message': error.description, 'code': error.code,
            'details': {'error_type': type(error).__name__, 'timestamp': datetime.now().isoformat(), 'error_message': str(error), 'suggestion': 'Please check your request and try again'}}, error.code

    @app.errorhandler(Exception)
    def handle_generic_error(error: Exception):
        """Handle generic errors."""
        logger.error(f"Unexpected Error: {str(error)}", exc_info=True)
        return {'status': 'error', 'message': 'An unexpected error occurred', 'code': 500,
            'details': {'error_type': type(error).__name__, 'timestamp': datetime.now().isoformat(), 'error_message': str(error),
                'suggestion': 'Please try again later or contact support if the issue persists'}}, 500
