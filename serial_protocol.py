"""Validation helpers for SeaSafe's newline-delimited serial messages."""

import json
import math
from datetime import datetime


EVENT_TYPES = {"STATUS", "SOS", "IMPACT_CANDIDATE", "TILT_CANDIDATE"}
REQUIRED_FIELDS = {
    "schema_version",
    "node_id",
    "event_id",
    "event_type",
    "timestamp",
    "gps_valid",
    "lat",
    "lon",
    "rssi",
    "snr",
    "hop_count",
    "test_mode",
}


class MessageValidationError(ValueError):
    """Raised when a serial line is not a supported SeaSafe event."""


def _is_number(value):
    """Booleans are not accepted as numeric telemetry values."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def parse_event_line(line):
    """Parse and validate one complete UTF-8 JSON line."""
    try:
        event = json.loads(line)
    except (json.JSONDecodeError, TypeError) as error:
        raise MessageValidationError(f"Malformed JSON: {error}") from error

    if not isinstance(event, dict):
        raise MessageValidationError("Message must be a JSON object.")

    missing_fields = REQUIRED_FIELDS - event.keys()
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise MessageValidationError(f"Missing required field(s): {missing}.")

    if (
        not isinstance(event["schema_version"], int)
        or isinstance(event["schema_version"], bool)
        or event["schema_version"] != 1
    ):
        raise MessageValidationError("schema_version must be 1.")
    for field in ("node_id", "event_id"):
        if not isinstance(event[field], str) or not event[field].strip():
            raise MessageValidationError(f"{field} must be a non-empty string.")
    if not isinstance(event["event_type"], str) or event["event_type"] not in EVENT_TYPES:
        raise MessageValidationError("event_type is not supported.")
    if event["timestamp"] is not None:
        if not isinstance(event["timestamp"], str):
            raise MessageValidationError("timestamp must be null or an ISO 8601 string.")
        try:
            datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
        except ValueError as error:
            raise MessageValidationError(
                "timestamp must be null or an ISO 8601 string."
            ) from error

    if not isinstance(event["gps_valid"], bool):
        raise MessageValidationError("gps_valid must be true or false.")
    latitude = event["lat"]
    longitude = event["lon"]
    if event["gps_valid"]:
        if not _is_number(latitude) or not _is_number(longitude):
            raise MessageValidationError("Valid GPS requires numeric lat and lon.")
        if not -90 <= latitude <= 90:
            raise MessageValidationError("lat must be between -90 and 90.")
        if not -180 <= longitude <= 180:
            raise MessageValidationError("lon must be between -180 and 180.")
    elif latitude is not None or longitude is not None:
        raise MessageValidationError("Invalid GPS requires null lat and lon.")

    for field in ("rssi", "snr"):
        if event[field] is not None and not _is_number(event[field]):
            raise MessageValidationError(f"{field} must be numeric or null.")
    if not isinstance(event["hop_count"], int) or isinstance(event["hop_count"], bool) or event["hop_count"] < 0:
        raise MessageValidationError("hop_count must be a non-negative integer.")
    if not isinstance(event["test_mode"], bool):
        raise MessageValidationError("test_mode must be true or false.")

    return event
