import json
import unittest
from serial_reader import SerialReader

class SerialReaderTests(unittest.TestCase):
    def test_constructor_and_empty_queue(self):
        reader = SerialReader("COM_TEST", 115200)
        self.assertEqual(reader.port, "COM_TEST")
        self.assertEqual(reader.baud, 115200)
        self.assertEqual(reader.drain_messages(), [])

    def test_queue_messages(self):
        reader = SerialReader("COM_TEST")
        reader._put({"kind": "state", "state": "Connected", "text": "test"})
        self.assertEqual(reader.drain_messages()[0]["state"], "Connected")

if __name__ == "__main__":
    unittest.main()
