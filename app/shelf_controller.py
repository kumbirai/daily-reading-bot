import json
import logging

from flask import Blueprint, jsonify
from .services.shelf_reader_service import retrieve_shelf_contents, retrieve_shelf_reading, retrieve_shelf_date

shelf_blueprint = Blueprint("shelf", __name__, url_prefix='/shelf')


@shelf_blueprint.route("", methods=["GET"])
def get_shelf():
    return handle_get_shelf()


@shelf_blueprint.route("/reading/<reading>", methods=["GET"])
def get_shelf_reading(reading):
    return handle_get_shelf_reading(reading)


@shelf_blueprint.route("/date/<date>", methods=["GET"])
def get_shelf_date(date):
    return handle_get_shelf_date(date)


def handle_get_shelf():
    readings_dict = retrieve_shelf_contents()
    return handle_readings(readings_dict)


def handle_get_shelf_reading(reading):
    readings_dict = retrieve_shelf_reading(reading)
    return handle_readings(readings_dict)


def handle_get_shelf_date(date):
    readings_dict = retrieve_shelf_date(date)
    return handle_readings(readings_dict)


def handle_readings(readings_dict):
    try:
        if readings_dict:
            return jsonify(readings_dict), 200
        else:
            return (
                jsonify({"status": "error", "message": "No content found"}),
                404,
            )
    except json.JSONDecodeError:
        logging.error("Failed to decode JSON")
        return jsonify({"status": "error", "message": "Invalid JSON provided"}), 400
