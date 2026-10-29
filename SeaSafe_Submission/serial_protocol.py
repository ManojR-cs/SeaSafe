import json

REQUIRED_FIELDS = {"node_id", "event_id", "event_type"}

def parse_serial_line(line):
    """Parse one newline-delimited JSON object; return (event, error)."""
    if isinstance(line, bytes):
        line = line.decode("utf-8", errors="replace")
    line = line.strip()
    if not line:
        return None, None
    try:
        event = json.loads(line)
    except (json.JSONDecodeError, TypeError) as exc:
        return None, f"Invalid JSON: {exc}"
    if not isinstance(event, dict):
        return None, "JSON value must be an object"
    missing = REQUIRED_FIELDS - event.keys()
    if missing:
        return None, "Missing required field(s): " + ", ".join(sorted(missing))
    for key in ("node_id", "event_id", "event_type"):
        if not isinstance(event.get(key), str) or not event[key].strip():
            return None, f"{key} must be a non-empty string"
    event.setdefault("timestamp", None)
    event.setdefault("gps_valid", False)
    event.setdefault("latitude", None)
    event.setdefault("longitude", None)
    event.setdefault("test_mode", False)
    return event, None
