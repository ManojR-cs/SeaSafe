"""Standard-library tests for the SeaSafe serial message simulator."""

import io
import json
import unittest
from contextlib import redirect_stdout

from serial_simulator import (
    EVENT_TYPES,
    MALFORMED_TEST_LINE,
    create_demo_sequence,
    create_event,
    print_json_lines,
)


class SerialSimulatorTests(unittest.TestCase):
    def test_each_event_type_serializes_as_valid_json(self):
        for index, event_type in enumerate(EVENT_TYPES, start=1):
            with self.subTest(event_type=event_type):
                event = create_event(event_type, f"TEST-{index}")
                output = io.StringIO()
                with redirect_stdout(output):
                    print_json_lines([event])
                line = output.getvalue()
                self.assertTrue(line.endswith("\n"))
                parsed = json.loads(line)
                self.assertEqual(parsed["event_type"], event_type)

    def test_invalid_gps_has_null_coordinates(self):
        event = create_event("STATUS", "TEST-GPS", gps_valid=False)

        self.assertFalse(event["gps_valid"])
        self.assertIsNone(event["lat"])
        self.assertIsNone(event["lon"])

    def test_demo_sequence_contains_repeated_event_id(self):
        events = create_demo_sequence()
        event_ids = [event["event_id"] for event in events]

        self.assertEqual(event_ids.count("SS-0002"), 2)
        self.assertIn("IMPACT_CANDIDATE", [event["event_type"] for event in events])
        self.assertIn("TILT_CANDIDATE", [event["event_type"] for event in events])

    def test_malformed_line_is_rejected_as_json(self):
        with self.assertRaises(json.JSONDecodeError):
            json.loads(MALFORMED_TEST_LINE)


if __name__ == "__main__":
    unittest.main()
