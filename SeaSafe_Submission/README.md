# SeaSafe — LoRa-Based Vessel-to-Shore Safety Prototype

SeaSafe is a prototype for sending vessel status and candidate incident alerts from an ESP32 vessel node to a shore station over LoRa. The shore receiver forwards received messages over USB serial to a local Streamlit dashboard.

The project is intended for learning, demonstration, and further development. **It is not a certified maritime safety system and must not replace approved marine distress equipment or procedures.**

## What it includes

- **Vessel transmitter firmware:** ESP32, RA-02 LoRa radio, GPS, MPU6050 motion sensor, SOS button, and optional microSD logging.
- **Shore receiver firmware:** ESP32 and RA-02 LoRa radio; forwards received JSON messages over USB serial and can log received packets to microSD.
- **Dashboard:** Streamlit application for viewing events and vessel locations.
- **Serial support:** JSON message parsing, serial reading, event history, and demonstration-event generation.
- **Documentation and tests:** Wiring reference, setup instructions, parser unit tests, and a test-report template.

> **Implementation status:** Source code is provided for these components, but source code alone does not prove that the physical hardware works. Compile and test each part on the actual boards before claiming it is functional.

## How it works

```text
[Vessel ESP32]
  GPS + MPU6050 + SOS button + optional microSD
              |
              v
       [RA-02 LoRa radio]
              ))))  wireless packet  ((((
       [RA-02 LoRa radio]
              |
              v
       [Shore ESP32 receiver]
              |
         USB serial
              |
              v
     [Local Streamlit dashboard]
```

The transmitter creates JSON events such as `STATUS`, `SOS`, `IMPACT_CANDIDATE`, and `TILT_CANDIDATE`. The receiver forwards valid-looking JSON payloads to its USB serial output. The dashboard parses the incoming messages and displays events.

The dashboard can run in demonstration mode without hardware. **Demonstration events are simulated and must not be interpreted as real vessel positions or emergencies.** A working dashboard does not, by itself, prove that a LoRa packet was transmitted or received.

## Repository structure

```text
SeaSafe_Submission/
├── app.py
├── sample_events.py
├── serial_protocol.py
├── serial_reader.py
├── serial_history.py
├── serial_simulator.py
├── requirements.txt
├── README.md
├── TEST_REPORT_TEMPLATE.md
├── docs/
│   └── WIRING.md
├── firmware/
│   ├── SeaSafeTransmitter/
│   │   └── SeaSafeTransmitter.ino
│   └── SeaSafeReceiver/
│       └── SeaSafeReceiver.ino
└── tests/
    ├── test_serial_protocol.py
    └── test_serial_reader.py
```

If this package is stored inside another Git repository, open a terminal in the `SeaSafe_Submission` directory to follow the instructions below.

## Hardware

For the full intended prototype:

- 2 compatible ESP32 development boards
- 2 RA-02 LoRa modules (SX1278-based)
- GPS module with UART output
- MPU6050 accelerometer/gyroscope module
- SOS push button
- microSD module and card (optional but supported by the sketches)
- Suitable 3.3 V power supply, wiring, and appropriate antennas

The example pin assignments are documented in [`docs/WIRING.md`](docs/WIRING.md). Confirm the exact pinout for your ESP32 board before wiring; ESP32-S3 boards may differ from classic ESP32 DevKit boards.

### Radio-frequency caution

The firmware examples use `433E6` (433 MHz) as a configurable value. This is **not a statement that the frequency or chosen radio settings are automatically permitted for your use**. Before transmitting, check current Indian WPC/DoT rules and applicable band, power, antenna, and equipment conditions. Attach a suitable antenna before transmitting, and do not transmit into an unterminated RF output.

## Software requirements

### Python dashboard

- Python 3.10 or a compatible version supported by the installed Streamlit release
- Packages listed in `requirements.txt`
- A local computer with USB access to the shore ESP32 for live serial operation

### ESP32 firmware

Install Arduino IDE and the ESP32 board package. Install these libraries using Arduino IDE Library Manager:

- **LoRa** by Sandeep Mistry
- **TinyGPSPlus**
- **Adafruit MPU6050**
- **Adafruit Unified Sensor**

`SPI`, `Wire`, and `SD` are provided by the ESP32 Arduino core. Library and board versions can affect compilation; record the versions used during testing.

## Run the dashboard on Windows

Open Command Prompt in the folder containing `app.py`:

```bat
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local address printed by Streamlit, usually `http://localhost:8501`.

### Live serial mode

1. Upload the receiver firmware to the shore ESP32.
2. Connect the receiver to the computer by USB.
3. Close Arduino Serial Monitor or any other program using the same COM port.
4. Select the receiver's COM port and baud rate **115200** in the dashboard.
5. Generate a test event from the transmitter and verify that the same event reaches the receiver serial output and appears in the dashboard.

A hosted dashboard such as Streamlit Community Cloud cannot directly access a COM port physically connected to your laptop. Use the local dashboard for direct USB serial access; use demonstration mode for a cloud-hosted walkthrough.

## Compile and upload the firmware

Compile each sketch separately in Arduino IDE:

- `firmware/SeaSafeReceiver/SeaSafeReceiver.ino` — upload to the shore receiver ESP32.
- `firmware/SeaSafeTransmitter/SeaSafeTransmitter.ino` — upload to the vessel ESP32.

Select the correct board and port for each device. Check the wiring against `docs/WIRING.md` and the exact board's pinout. The receiver and transmitter must use compatible radio settings, including frequency and the LoRa library configuration.

The sketches are an integration starting point. They have **not been certified or physically verified by the existence of these files**. Compilation, initialization messages, and actual over-the-air packet reception are separate checks.

## Event format

An example event is:

```json
{
  "node_id": "VESSEL-01",
  "event_id": "VESSEL-01-12",
  "event_type": "SOS",
  "timestamp": null,
  "latitude": 12.95,
  "longitude": 74.72,
  "gps_valid": true,
  "test_mode": false,
  "message": "SOS button pressed"
}
```

- `node_id`: identifier for the sending node.
- `event_id`: event identifier used for duplicate detection.
- `event_type`: `STATUS`, `SOS`, `IMPACT_CANDIDATE`, or `TILT_CANDIDATE` in the supplied firmware.
- `timestamp`: UTC time when GPS date/time is valid; otherwise `null`.
- `latitude` and `longitude`: coordinates when a recent GPS fix is available; otherwise `null`.
- `gps_valid`: whether the firmware considers the GPS fix recent and valid.
- `test_mode`: identifies demonstration/test data where used.
- `message`: human-readable event description.

An `IMPACT_CANDIDATE` or `TILT_CANDIDATE` is only a sensor-threshold indication, not a confirmed accident. The thresholds require calibration and controlled testing.

## Run the Python tests

From the directory containing `tests/`:

```bat
python -m unittest discover -s tests -v
```

These tests cover limited Python parsing and serial-reader behavior. They do **not** test ESP32 firmware, RF transmission, GPS accuracy, sensor detection, SD persistence, or real-world range. Record the actual output and any failures in `TEST_REPORT_TEMPLATE.md`.

## Hardware validation checklist

Only mark a step complete after observing and recording its result.

- [ ] Dashboard starts locally.
- [ ] Python unit tests pass.
- [ ] Receiver sketch compiles and uploads to the intended board.
- [ ] Transmitter sketch compiles and uploads to the intended board.
- [ ] Receiver reports LoRa initialization status.
- [ ] A physical LoRa packet from the transmitter is received by the receiver.
- [ ] GPS fix and coordinates are verified outdoors.
- [ ] SOS button generates an event.
- [ ] MPU6050 candidate events are checked under controlled conditions.
- [ ] microSD logs are present and remain readable after reboot.
- [ ] A real received packet appears in the local dashboard.
- [ ] Frequency and radio-power compliance have been checked.

Use the test-report template to capture board models, library versions, wiring, serial logs, photos, and results.

## Known limitations

- No end-to-end acknowledgement or retry protocol; transmitted packets can be lost.
- No encryption or device authentication; do not send sensitive data.
- No guaranteed coverage, delivery, or emergency-response integration.
- GPS may not obtain a fix indoors or under obstructed sky.
- Motion thresholds are heuristic and can cause missed events or false positives.
- microSD operation depends on module wiring, card format, power, and successful initialization.
- The example sketches use fixed pin assignments and a fixed node ID that may need changing for the chosen boards and multiple vessels.
- The prototype is not a replacement for approved maritime distress equipment, radio procedures, or emergency services.

## Contributing and reuse

You can fork the repository, adapt the code to your hardware, and submit improvements. Preserve clear separation between simulated and real data, document any pin or protocol changes, and include reproducible test evidence for hardware claims. Check the repository's selected license before redistributing or reusing the code; if no license is included, do not assume that public visibility grants permission to reuse it.

## Project status

SeaSafe is a prototype intended for demonstration and further development. Document what has actually been tested, what remains unverified, and the exact hardware/software versions used. Do not claim operational maritime safety performance without rigorous testing and appropriate certification.
