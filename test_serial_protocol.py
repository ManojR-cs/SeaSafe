"""Tests for live serial message validation and event deduplication."""

import json
import unittest

from serial_history import EventHistory
from serial_protocol import MessageValidationError, parse_event_line
from serial_reader import SerialReader


# The supplied example had placeholder strings without JSON values. This is
# the same field layout with representative valid values for an actual JSON test.
EXAMPLE_JSON_LINE = (
    '{"schema_version":1,"node_id":"TEST-ESP32-S3",'
    '"event_id":"USB-000126","event_type":"STATUS",'
    '"timestamp":"2026-10-28T09:00:00Z","gps_valid":false,'
    '"lat":null,"lon":null,"rssi":-71,"snr":8.5,'
    '"hop_count":0,"test_mode":true}'
)


class SerialProtocolTests(unittest.TestCase):
    def test_example_json_line_is_valid_and_test_labeled(self):
        event = parse_event_line(EXAMPLE_JSON_LINE)

        self.assertEqual(event["node_id"], "TEST-ESP32-S3")
        self.assertEqual(event["event_id"], "USB-000126")
        self.assertEqual(event["event_type"], "STATUS")
        self.assertTrue(event["test_mode"])
        self.assertIsNone(event["lat"])
        self.assertIsNone(event["lon"])

    def test_status_event_accepts_null_timestamp(self):
        event = json.loads(EXAMPLE_JSON_LINE)
        event["timestamp"] = None

        parsed = parse_event_line(json.dumps(event))

        self.assertEqual(parsed["event_type"], "STATUS")
        self.assertIsNone(parsed["timestamp"])

    def test_iso_8601_timestamp_is_accepted(self):
        event = parse_event_line(EXAMPLE_JSON_LINE)

        self.assertEqual(event["timestamp"], "2026-10-28T09:00:00Z")

    def test_invalid_non_null_timestamp_is_rejected(self):
        event = json.loads(EXAMPLE_JSON_LINE)
        event["timestamp"] = "not-a-timestamp"

        with self.assertRaisesRegex(MessageValidationError, "ISO 8601"):
            parse_event_line(json.dumps(event))

    def test_malformed_json_is_rejected(self):
        with self.assertRaisesRegex(MessageValidationError, "Malformed JSON"):
            parse_event_line('{"event_type":"SOS", broken')

    def test_missing_required_field_is_rejected(self):
        event = json.loads(EXAMPLE_JSON_LINE)
        del event["node_id"]

        with self.assertRaisesRegex(MessageValidationError, "node_id"):
            parse_event_line(json.dumps(event))

    def test_invalid_coordinate_ranges_are_rejected(self):
        event = json.loads(EXAMPLE_JSON_LINE)
        event.update(gps_valid=True, lat=91, lon=74.8)

        with self.assertRaisesRegex(MessageValidationError, "lat must be between"):
            parse_event_line(json.dumps(event))

    def test_gps_valid_requires_coordinates_and_invalid_requires_nulls(self):
        event = json.loads(EXAMPLE_JSON_LINE)
        event.update(gps_valid=True, lat=None, lon=None)
        with self.assertRaisesRegex(MessageValidationError, "numeric lat and lon"):
            parse_event_line(json.dumps(event))

        event.update(gps_valid=False, lat=12.9, lon=74.8)
        with self.assertRaisesRegex(MessageValidationError, "null lat and lon"):
            parse_event_line(json.dumps(event))

    def test_test_mode_must_be_boolean(self):
        event = json.loads(EXAMPLE_JSON_LINE)
        event["test_mode"] = "true"

        with self.assertRaisesRegex(MessageValidationError, "test_mode"):
            parse_event_line(json.dumps(event))

    def test_duplicate_uses_node_id_and_event_id(self):
        event = parse_event_line(EXAMPLE_JSON_LINE)
        history = EventHistory(max_events=2)

        self.assertTrue(history.add(event))
        self.assertFalse(history.add(event))
        self.assertEqual(history.duplicate_count, 1)
        other_node = dict(event, node_id="OTHER-ESP32")
        self.assertTrue(history.add(other_node))

    def test_reader_combines_partial_reads_before_parsing(self):
        reader = SerialReader("COM-test", 115200)
        encoded_line = (EXAMPLE_JSON_LINE + "\n").encode("utf-8")

        class ChunkedConnection:
            def __init__(self):
                self.chunks = [encoded_line[:30], encoded_line[30:]]

            def read(self, _size):
                chunk = self.chunks.pop(0)
                if not self.chunks:
                    reader._stop_event.set()
                return chunk

        reader._read_connection(ChunkedConnection())
        messages = reader.drain_messages()

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["kind"], "event")
        self.assertEqual(messages[0]["event"]["event_id"], "USB-000126")


if __name__ == "__main__":
    unittest.main()
