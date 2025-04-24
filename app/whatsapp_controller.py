import json
import logging
from flask import Blueprint, request, current_app
from flask_restx import Api, Resource, fields
from .decorators.security import signature_required
from .utils.whatsapp_utils import (
    process_whatsapp_message,
    is_valid_whatsapp_message,
)
from .utils.error_handlers import ValidationError, WhatsAppAPIError

logger = logging.getLogger(__name__)
webhook_blueprint = Blueprint("webhook", __name__, url_prefix='/webhook')
api = Api(webhook_blueprint,
    title='WhatsApp Webhook API',
    version='1.0',
    description='API for handling WhatsApp webhook events'
)

# Define models for Swagger documentation
error_model = api.model('Error', {
    'status': fields.String(description='Status of the response', example='error'),
    'message': fields.String(description='Error message', example='Invalid signature'),
    'code': fields.Integer(description='HTTP status code', example=403),
    'details': fields.Raw(description='Additional error details', example={
        'error_type': 'ValidationError',
        'timestamp': '2025-04-24T17:21:45.227000',
        'error_message': 'Invalid signature provided',
        'suggestion': 'Please check your request signature and try again'
    })
})

success_model = api.model('Success', {
    'status': fields.String(description='Status of the response', example='success'),
    'message': fields.String(description='Success message')
})

webhook_verification_model = api.model('WebhookVerification', {
    'hub.mode': fields.String(description='Verification mode', example='subscribe'),
    'hub.verify_token': fields.String(description='Verification token'),
    'hub.challenge': fields.String(description='Challenge token')
})

# Define namespaces
ns = api.namespace('', description='WhatsApp webhook operations')

@ns.route('/verify')
class WebhookVerification(Resource):
    @ns.doc('webhook_verify',
        params={
            'hub.mode': 'Verification mode',
            'hub.verify_token': 'Verification token',
            'hub.challenge': 'Challenge token'
        },
        responses={
            200: ('Verification Successful', success_model),
            400: ('Invalid Parameters', error_model),
            500: ('Internal Server Error', error_model)
        })
    @ns.marshal_with(success_model)
    def get(self):
        """Handle GET requests for webhook verification."""
        return verify()

@ns.route('/message')
class WebhookMessage(Resource):
    @ns.doc('webhook_message',
        responses={
            200: ('Message Processed Successfully', success_model),
            400: ('Invalid Request', error_model),
            500: ('Internal Server Error', error_model)
        })
    @ns.marshal_with(success_model)
    @signature_required
    def post(self):
        """Handle POST requests for incoming messages."""
        return handle_message()

def handle_message():
    """
    Handle incoming webhook events from the WhatsApp API.

    This function processes incoming WhatsApp messages and other events,
    such as delivery statuses. If the event is a valid message, it gets
    processed. If the incoming payload is not a recognized WhatsApp event,
    an error is returned.

    Every message send will trigger 4 HTTP requests to your webhook: message, sent, delivered, read.

    Returns:
        response: A tuple containing a JSON response and an HTTP status code.
        
    Raises:
        ValidationError: If the request is invalid or not a valid WhatsApp event
    """
    body = request.get_json()
    logger.info(f"Received webhook request: {json.dumps(body, indent=2)}")

    # Check if it's a WhatsApp status update
    if (
            body.get("entry", [{}])[0]
                    .get("changes", [{}])[0]
                    .get("value", {})
                    .get("statuses")
    ):
        logger.info("Received a WhatsApp status update")
        return {
            "status": "success",
            "message": "Status update received"
        }, 200

    if not is_valid_whatsapp_message(body):
        raise ValidationError("Not a valid WhatsApp API event")

    process_whatsapp_message(body)
    return {
        "status": "success",
        "message": "Message processed successfully"
    }, 200

def verify():
    """
    Verify the webhook for WhatsApp API.
    
    This function handles the verification request from WhatsApp API
    to confirm the webhook endpoint is valid.
    
    Returns:
        response: The challenge token or an error response.
        
    Raises:
        ValidationError: If verification parameters are missing or invalid
    """
    # Parse params from the webhook verification request
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    logger.info(f"Verification request - mode: {mode}, token: {token}, challenge: {challenge}")

    if not mode or not token:
        raise ValidationError("Missing verification parameters")

    if mode == "subscribe" and token == current_app.config["VERIFY_TOKEN"]:
        logger.info("Webhook verified successfully")
        return {
            "status": "success",
            "message": "Webhook verified successfully",
            "challenge": challenge
        }, 200
    else:
        logger.warning("Verification failed - invalid token or mode")
        raise ValidationError("Verification failed")
