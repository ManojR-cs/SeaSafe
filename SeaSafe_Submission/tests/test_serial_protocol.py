import unittest
from serial_protocol import parse_serial_line

class ProtocolTests(unittest.TestCase):
    def test_valid_event(self):
        event, error = parse_serial_line('{"node_id":"N1","event_id":"E1","event_type":"SOS"}')
        self.assertIsNone(error)
        self.assertEqual(event["event_type"], "SOS")
        self.assertFalse(event["gps_valid"])

    def test_invalid_json(self):
        event, error = parse_serial_line("{nope")
        self.assertIsNone(event)
        self.assertIn("Invalid JSON", error)

    def test_missing_fields(self):
        event, error = parse_serial_line('{"node_id":"N1"}')
        self.assertIsNone(event)
        self.assertIn("Missing required", error)

    def test_non_object(self):
        event, error = parse_serial_line("[]")
        self.assertIsNone(event)
        self.assertIn("object", error)

if __name__ == "__main__":
    unittest.main()
