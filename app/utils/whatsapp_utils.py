import json
import logging
import re

import requests
from flask import current_app

from app.services.daily_reading_service import generate_daily_reading_responses
from app.services.random_zen_quotes_service import generate_random_zen_quote

logger = logging.getLogger(__name__)


def log_http_response(response):
    logger.info(f"Status: {response.status_code}")
    logger.info(f"Content-type: {response.headers.get('content-type')}")
    logger.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    return json.dumps({"messaging_product": "whatsapp", "recipient_type": "individual", "to": recipient, "type": "text", "text": {"preview_url": False, "body": text}, })


def send_read_receipt(message):
    message_id = message["id"]
    data = json.dumps({"messaging_product": "whatsapp", "status": "read", "message_id": message_id})
    send_message(data)


def send_message(data):
    """
    Send a message to the WhatsApp API.
    
    Args:
        data: The message data to send
        
    Returns:
        requests.Response: The response from the WhatsApp API
        
    Raises:
        requests.Timeout: If the request times out
        requests.RequestException: If the request fails
    """
    headers = {"Content-type": "application/json", "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}", }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"
    response = requests.post(url, data=data, headers=headers, timeout=10)  # 10 seconds timeout as an example
    response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
    log_http_response(response)
    return response


def process_text_for_whatsapp(text):
    # Remove brackets
    pattern = r"\【.*?\】"
    # Substitute the pattern with an empty string
    text = re.sub(pattern, "", text).strip()

    # Pattern to find double asterisks including the word(s) in between
    pattern = r"\*\*(.*?)\*\*"

    # Replacement pattern with single asterisks
    replacement = r"*\1*"

    # Substitute occurrences of the pattern with the replacement
    whatsapp_style_text = re.sub(pattern, replacement, text)

    return whatsapp_style_text


def process_whatsapp_message(body):
    """
    Process an incoming WhatsApp message.
    
    Args:
        body: The message body from the WhatsApp API
        
    Raises:
        KeyError: If required message fields are missing (e.g., if the message structure is invalid)
        requests.RequestException: If sending the message fails
    """
    wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]

    message = body["entry"][0]["changes"][0]["value"]["messages"][0]
    message_body = message["text"]["body"]

    send_read_receipt(message)

    responses = generate_daily_reading_responses(message_body, wa_id)
    if responses:
        for response in responses:
            data = get_text_message_input(wa_id, response)
            send_message(data)
    else:
        data = get_text_message_input(wa_id, generate_random_zen_quote())
        send_message(data)


def is_valid_whatsapp_message(body):
    """
    Check if the incoming webhook event has a valid WhatsApp message structure.
    """
    return (body.get("object") and body.get("entry") and body["entry"][0].get("changes") and body["entry"][0]["changes"][0].get("value") and body["entry"][0]["changes"][0]["value"].get("messages") and
            body["entry"][0]["changes"][0]["value"]["messages"][0])
