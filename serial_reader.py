"""Background PySerial reader with reconnects and newline framing."""

import queue
import threading

from serial_protocol import MessageValidationError, parse_event_line


MAX_LINE_BYTES = 64 * 1024


class SerialReader:
    """Read a selected serial port without blocking Streamlit's script thread."""

    def __init__(self, port, baud_rate):
        self.port = port
        self.baud_rate = baud_rate
        self.messages = queue.Queue(maxsize=1000)
        self._stop_event = threading.Event()
        self._connection_lock = threading.Lock()
        self._connection = None
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        """Request shutdown and close the port to unblock a pending read."""
        self._stop_event.set()
        with self._connection_lock:
            if self._connection is not None:
                try:
                    self._connection.close()
                except Exception:
                    pass
        if self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def drain_messages(self):
        """Return messages currently waiting for the Streamlit fragment."""
        drained = []
        while True:
            try:
                drained.append(self.messages.get_nowait())
            except queue.Empty:
                return drained

    def _post(self, message):
        """Keep the cross-thread queue bounded if the UI is paused."""
        try:
            self.messages.put_nowait(message)
        except queue.Full:
            try:
                self.messages.get_nowait()
            except queue.Empty:
                pass
            try:
                self.messages.put_nowait(
                    {"kind": "queue_warning", "text": "Reader queue full; oldest queued item dropped."}
                )
            except queue.Full:
                pass

    def _run(self):
        try:
            import serial
        except ImportError:
            self._post({"kind": "state", "state": "PySerial is not installed"})
            return

        while not self._stop_event.is_set():
            connection = None
            try:
                connection = serial.Serial(self.port, self.baud_rate, timeout=0.2)
                with self._connection_lock:
                    if self._stop_event.is_set():
                        connection.close()
                        return
                    self._connection = connection
                self._post({"kind": "state", "state": "Connected"})
                self._read_connection(connection)
            except (serial.SerialException, OSError) as error:
                if not self._stop_event.is_set():
                    self._post(
                        {"kind": "state", "state": "Reconnecting", "text": str(error)}
                    )
            except Exception as error:
                if not self._stop_event.is_set():
                    self._post(
                        {"kind": "state", "state": "Reader error; reconnecting", "text": str(error)}
                    )
            finally:
                with self._connection_lock:
                    self._connection = None
                if connection is not None:
                    try:
                        connection.close()
                    except Exception:
                        pass

            if not self._stop_event.is_set():
                self._stop_event.wait(2.0)

        self._post({"kind": "state", "state": "Disconnected"})

    def _read_connection(self, connection):
        """Accumulate partial reads and parse only complete newline-terminated lines."""
        partial_line = bytearray()
        while not self._stop_event.is_set():
            chunk = connection.read(256)
            if not chunk:
                continue
            partial_line.extend(chunk)

            while b"\n" in partial_line:
                raw_line, _, remainder = partial_line.partition(b"\n")
                partial_line = bytearray(remainder)
                if not raw_line.strip():
                    continue
                if len(raw_line) > MAX_LINE_BYTES:
                    self._post(
                        {"kind": "parse_error", "text": "Input line exceeded 64 KiB and was discarded."}
                    )
                    continue
                self._handle_line(raw_line.rstrip(b"\r"))

            if len(partial_line) > MAX_LINE_BYTES:
                self._post(
                    {"kind": "parse_error", "text": "Input line exceeded 64 KiB and was discarded."}
                )
                partial_line.clear()

        # An incomplete final line is intentionally discarded during shutdown.

    def _handle_line(self, raw_line):
        try:
            line = raw_line.decode("utf-8")
        except UnicodeDecodeError as error:
            self._post({"kind": "parse_error", "text": f"Input was not UTF-8: {error}"})
            return

        try:
            event = parse_event_line(line)
        except MessageValidationError as error:
            self._post({"kind": "parse_error", "text": str(error)})
            return

        self._post({"kind": "event", "event": event})
