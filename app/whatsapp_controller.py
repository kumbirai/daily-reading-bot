import json
import logging

from flask import Blueprint, request, jsonify, current_app

from .decorators.security import signature_required
from .utils.error_handlers import ValidationError, WhatsAppAPIError
from .utils.whatsapp_utils import (
    process_whatsapp_message,
    is_valid_whatsapp_message,
)

logger = logging.getLogger(__name__)
webhook_blueprint = Blueprint("webhook", __name__, url_prefix='/webhook')


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
    """
    try:
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
            return jsonify({"status": "success", "message": "Status update received"}), 200

        if not is_valid_whatsapp_message(body):
            raise ValidationError("Not a valid WhatsApp API event")

        process_whatsapp_message(body)
        return jsonify({"status": "success", "message": "Message processed successfully"}), 200

    except json.JSONDecodeError:
        logger.error("Failed to decode JSON from request body")
        raise ValidationError("Invalid JSON provided")
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Error processing WhatsApp message: {str(e)}", exc_info=True)
        raise WhatsAppAPIError("Failed to process WhatsApp message")


def verify():
    """
    Verify the webhook for WhatsApp API.
    
    This function handles the verification request from WhatsApp API
    to confirm the webhook endpoint is valid.
    
    Returns:
        response: The challenge token or an error response.
    """
    try:
        # Parse params from the webhook verification request
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        logger.info(f"Verification request - mode: {mode}, token: {token}, challenge: {challenge}")

        if not mode or not token:
            raise ValidationError("Missing verification parameters")

        if mode == "subscribe" and token == current_app.config["VERIFY_TOKEN"]:
            logger.info("Webhook verified successfully")
            return challenge, 200
        else:
            logger.warning("Verification failed - invalid token or mode")
            raise ValidationError("Verification failed")

    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Error during webhook verification: {str(e)}", exc_info=True)
        raise WhatsAppAPIError("Failed to verify webhook")


@webhook_blueprint.route("", methods=["GET"])
def webhook_get():
    """Handle GET requests for webhook verification."""
    return verify()


@webhook_blueprint.route("", methods=["POST"])
@signature_required
def webhook_post():
    """Handle POST requests for incoming messages."""
    return handle_message()
