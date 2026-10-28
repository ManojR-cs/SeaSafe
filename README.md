# SeaSafe Shore Dashboard — Milestone 1

A local Streamlit dashboard with a simulated demo feed and an optional USB serial input from an ESP32. Live mode reads JSON lines from the selected serial port. It does not implement LoRa, and a USB message does not confirm radio reception or emergency delivery.

## Windows installation and launch

Open Command Prompt in this project folder and run:

```bat
py -3 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Streamlit prints a local address (usually `http://localhost:8501`) to open in a browser. Stop the server with `Ctrl+C` in Command Prompt. If you prefer not to activate the environment, use its Python directly:

```bat
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

The requirements install Streamlit and PySerial. The dashboard needs Streamlit 1.37 or newer for its periodic live-status refresh.

## Connect the ESP32

1. Close Arduino Serial Monitor or any other program using the board's COM port; Windows normally allows only one program to open a port at a time.
2. Start the dashboard using the commands above.
3. Select **Live ESP32**, choose the ESP32 port shown in the dropdown, and select the board's baud rate (default: **115200**).
4. Click **Connect**. Use **Refresh ports** if the board was connected after opening the dashboard. Click **Disconnect** before changing ports or returning to Demo Mode.

The app discovers ports through PySerial, so it does not assume a fixed port such as COM5. The reader runs in a background thread with a short serial timeout; a Streamlit fragment checks its queue once per second. It buffers partial reads until a newline arrives, validates each complete JSON line, and retries the selected port after a disconnect. Switching back to Demo Mode or clicking Disconnect stops the reader and closes the port. Live mode never substitutes sample events when the port is unavailable.

Every accepted message must be one JSON object per line with these fields: `schema_version` (currently `1`), `node_id`, `event_id`, `event_type`, ISO 8601 `timestamp`, boolean `gps_valid`, `lat`, `lon`, `rssi`, `snr`, non-negative integer `hop_count`, and boolean `test_mode`. Event types are STATUS, SOS, IMPACT_CANDIDATE, and TILT_CANDIDATE. Coordinates must be numeric and within latitude/longitude ranges when GPS is valid; when it is invalid, both must be JSON `null`. `rssi` and `snr` may be `null` and are displayed as unavailable.

The example in the project request used bare placeholder keys such as `"timestamp"` without JSON values, so it was not valid JSON as written. The protocol tests use the same field layout with representative values. Ensure the ESP32 prints complete, valid JSON objects followed by `\n`.

Messages with `test_mode: true` are visibly labeled **HARDWARE TEST DATA** and excluded from the operational SOS count. This flag must be present and boolean on every message. The current ESP32 is reported as sending STATUS messages only. Do not treat a received USB STATUS line as proof that GPS, LoRa, SOS handling, acknowledgements, or emergency delivery work. Acknowledgement data is unavailable because the current message schema does not provide it.

Live history is limited to the latest 200 unique events. Duplicate detection uses `(node_id, event_id)` and remembers up to 5,000 recent identifiers per dashboard session. Malformed or invalid lines increment the parse-error count. Partial lines are held until completed; an incomplete line is discarded when disconnecting. If a line exceeds 64 KiB, it is discarded and counted as a parse error.

Run the automated checks from Command Prompt in the project folder:

```bat
python -m unittest -v
python -m py_compile app.py serial_protocol.py serial_reader.py serial_history.py
```

## Serial message simulator

`serial_simulator.py` prints simulated JSON Lines messages to the terminal. Each valid message is one JSON object followed by a newline. It uses only the Python standard library and does not open a COM port or connect to a device.

From Command Prompt, with the project's virtual environment activated:

```bat
REM Generate one STATUS event (the default event type)
python serial_simulator.py

REM Generate one SOS event
python serial_simulator.py --event SOS

REM Generate one STATUS event with GPS unavailable and null coordinates
python serial_simulator.py --event STATUS --gps-unavailable

REM Generate a short sequence with all event types and a repeated event ID
python serial_simulator.py --sequence

REM Print a deliberately malformed JSON line for parser error testing only
python serial_simulator.py --malformed-line
```

The malformed-line option is deliberately separate from valid event generation. Do not pass its output to a parser as a valid event. All simulator output is test data: it does not prove real radio transmission, reception, or emergency delivery.

Run the simulator tests with:

```bat
python -m unittest -v test_serial_simulator
```

## Code flow

1. `sample_events.py` holds the dashboard's demo STATUS, SOS, IMPACT_CANDIDATE, and TILT_CANDIDATE packets.
2. In Demo Mode, `app.py` renders those existing examples. In Live ESP32 mode, it starts `serial_reader.py` and displays only messages received from the selected USB serial port.
3. `serial_protocol.py` validates each complete JSON line. `serial_history.py` keeps a bounded list and deduplicates by node and event ID.
4. The serial reader runs away from Streamlit's UI thread and publishes complete messages/errors to a queue. A periodic Streamlit fragment updates the live display without blocking the page on serial input.

The demo SOS examples are not real incidents. Candidate events are possible sensor triggers, not confirmed impact or tilt incidents. Simulator output also remains test data; it does not prove real radio transmission, reception, or emergency delivery.

## Files

- `app.py` — Streamlit interface and display logic.
- `sample_events.py` — Separate sample packet data.
- `serial_simulator.py` — Command-line JSONL generator for parser preparation; no hardware connection.
- `test_serial_simulator.py` — Standard-library simulator tests.
- `serial_protocol.py` — Live-message schema and validation.
- `serial_reader.py` — Background USB serial reader and reconnect handling.
- `serial_history.py` — Bounded event history and deduplication.
- `test_serial_protocol.py` — Protocol validation and deduplication tests.
- `requirements.txt` — Streamlit and PySerial dependencies.
