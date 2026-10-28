"""Print simulated shore-receiver JSON-lines messages for parser testing."""

import argparse
import json
from datetime import datetime, timezone


EVENT_TYPES = (
    "STATUS",
    "SOS",
    "IMPACT_CANDIDATE",
    "TILT_CANDIDATE",
)

# This input is intentionally not JSON. It is available only through its own
# command-line option, so normal event generation never emits malformed data.
MALFORMED_TEST_LINE = '{"event_type": "SOS", broken json'


def create_event(event_type, event_id, gps_valid=True):
    """Build one event using the planned shore-side serial message schema."""
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Unsupported event type: {event_type}")

    if gps_valid:
        latitude = 12.9716
        longitude = 74.8194
    else:
        # Never provide placeholder coordinates when the simulated fix is invalid.
        latitude = None
        longitude = None

    return {
        "schema_version": 1,
        "node_id": "SS-BOAT-07",
        "event_id": event_id,
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "gps_valid": gps_valid,
        "lat": latitude,
        "lon": longitude,
        "rssi": -71,
        "snr": 8.5,
        "hop_count": 1,
    }


def create_demo_sequence():
    """Return several valid messages, including a deliberate duplicate ID."""
    return [
        create_event("STATUS", "SS-0001"),
        create_event("SOS", "SS-0002"),
        create_event("STATUS", "SS-0003", gps_valid=False),
        create_event("IMPACT_CANDIDATE", "SS-0004"),
        create_event("TILT_CANDIDATE", "SS-0005"),
        # Repeated IDs let a parser exercise its duplicate-event handling.
        create_event("SOS", "SS-0002"),
    ]


def print_json_lines(events):
    """Write one compact JSON object and newline for each event."""
    for event in events:
        print(json.dumps(event, separators=(",", ":")))


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Print simulated SeaSafe messages; no COM port or hardware is used."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--event",
        choices=EVENT_TYPES,
        help="print one valid event (default: STATUS)",
    )
    mode.add_argument(
        "--sequence",
        action="store_true",
        help="print a short valid sequence, including an event ID repeated twice",
    )
    mode.add_argument(
        "--malformed-line",
        action="store_true",
        help="print one intentionally invalid JSON line for parser testing only",
    )
    parser.add_argument(
        "--gps-unavailable",
        action="store_true",
        help="for a single event, set gps_valid false and lat/lon to null",
    )
    return parser.parse_args()


def main():
    arguments = parse_arguments()

    if arguments.malformed_line:
        if arguments.gps_unavailable:
            raise SystemExit("--gps-unavailable applies only to a valid single event.")
        print(MALFORMED_TEST_LINE)
        return

    if arguments.sequence:
        if arguments.gps_unavailable:
            raise SystemExit("--gps-unavailable is already included in --sequence.")
        print_json_lines(create_demo_sequence())
        return

    event_type = arguments.event or "STATUS"
    event = create_event(event_type, "SS-0001", gps_valid=not arguments.gps_unavailable)
    print_json_lines([event])


if __name__ == "__main__":
    main()
