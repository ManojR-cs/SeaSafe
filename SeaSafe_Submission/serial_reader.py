import json
import queue
import threading
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None

class SerialReader:
    """Background serial reader exposing app.py's drain_messages() interface."""
    def __init__(self, port, baud=115200):
        self.port = port
        self.baud = int(baud)
        self._messages = queue.Queue(maxsize=2000)
        self._stop_event = threading.Event()
        self._thread = None
        self._serial = None

    @staticmethod
    def available_ports():
        if list_ports is None:
            return []
        return sorted(p.device for p in list_ports.comports())

    def _put(self, item):
        try:
            self._messages.put_nowait(item)
        except queue.Full:
            # Drop one oldest message and make room for the newest status/data.
            try:
                self._messages.get_nowait()
            except queue.Empty:
                pass
            try:
                self._messages.put_nowait(item)
            except queue.Full:
                pass

    def start(self):
        if serial is None:
            raise RuntimeError("pyserial is not installed. Run: pip install -r requirements.txt")
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        try:
            self._serial = serial.Serial(self.port, self.baud, timeout=1)
            self._put({"kind": "state", "state": "Connected", "text": f"{self.port} at {self.baud} baud"})
            while not self._stop_event.is_set():
                raw = self._serial.readline()
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    if not isinstance(event, dict):
                        raise ValueError("JSON value must be an object")
                    for key in ("node_id", "event_id", "event_type"):
                        if not isinstance(event.get(key), str) or not event[key].strip():
                            raise ValueError(f"missing or invalid {key}")
                    event.setdefault("timestamp", None)
                    event.setdefault("gps_valid", False)
                    event.setdefault("latitude", None)
                    event.setdefault("longitude", None)
                    event.setdefault("test_mode", False)
                    self._put({"kind": "event", "event": event})
                except (json.JSONDecodeError, ValueError) as exc:
                    self._put({"kind": "parse_error", "text": f"{exc}: {line[:300]}"})
        except Exception as exc:
            self._put({"kind": "state", "state": "Error", "text": str(exc)})
        finally:
            if self._serial is not None:
                try:
                    self._serial.close()
                except Exception:
                    pass
                self._serial = None
            if not self._stop_event.is_set():
                self._put({"kind": "state", "state": "Disconnected", "text": "Serial reader stopped"})

    def drain_messages(self):
        messages = []
        while True:
            try:
                messages.append(self._messages.get_nowait())
            except queue.Empty:
                break
        return messages

    def stop(self):
        self._stop_event.set()
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        self._thread = None
        self._put({"kind": "state", "state": "Disconnected", "text": "Disconnected by user"})
