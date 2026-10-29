# SeaSafe — LoRa Vessel-to-Shore Safety Demonstrator

SeaSafe is a prototype architecture for sending vessel status and candidate incident events from an ESP32 vessel node to a shore ESP32 receiver over LoRa. The receiver forwards newline-delimited JSON to a local Streamlit dashboard. A GPS receiver can attach coordinates; an MPU6050 can flag acceleration/tilt candidates; microSD can retain JSONL event records.

**Important:** This repository is a development/demo package, not a certified maritime safety system. The hardware source is provided but has not been physically verified in this package. Do not represent radio range, GPS accuracy, sensor detection, persistent logging, or emergency delivery as tested until you test and document each one.

## Repository layout

```text
SeaSafe/
├── app.py
├── sample_events.py
├── serial_protocol.py
├── serial_reader.py
├── serial_history.py
├── serial_simulator.py
├── requirements.txt
├── firmware/
│   ├── SeaSafeTransmitter/SeaSafeTransmitter.ino
│   └── SeaSafeReceiver/SeaSafeReceiver.ino
├── docs/WIRING.md
└── tests/test_serial_protocol.py
```

## Architecture

1. **Vessel node:** reads GPS serial data, samples MPU6050, monitors the SOS button, and emits JSON events.
2. **LoRa link:** sends the JSON payload from the vessel RA-02 to the shore RA-02.
3. **Shore node:** prints received payloads to USB serial and optionally logs received packets and radio RSSI/SNR to microSD.
4. **Local dashboard:** reads JSON lines from the receiver's serial port and displays events.

The receiver forwards payloads unchanged; the dashboard parser checks the required `node_id`, `event_id`, and `event_type` fields. Dashboard availability does not prove radio delivery.

## Firmware dependencies

Install these libraries in Arduino IDE Library Manager:
- LoRa by Sandeep Mistry
- TinyGPSPlus
- Adafruit MPU6050
- Adafruit Unified Sensor

`SPI`, `Wire`, and `SD` are included with the ESP32 Arduino core. Select the correct ESP32 board and COM port. Compile each sketch separately. The two sketches use a 433 MHz example frequency; confirm legal frequency/power conditions before enabling radio transmission.

## Dashboard setup on Windows

Open Command Prompt in the repository directory:

```bat
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL Streamlit prints, usually `http://localhost:8501`. Connect the **shore receiver ESP32** by USB, choose its COM port, and use 115200 baud. Close Arduino Serial Monitor first because only one application can usually own the COM port at a time.

The hosted Streamlit service cannot access a USB serial port physically connected to your laptop. Use local Streamlit for live serial reception. Use demo mode for a cloud-hosted presentation.

## Hardware bring-up order

1. Inspect wiring against `docs/WIRING.md` and the exact board pinout.
2. Compile and upload the receiver sketch. Open Serial Monitor at 115200 and check its startup JSON. A `lora=ready` message only means library initialization succeeded; it does not prove reception.
3. Compile and upload the transmitter sketch to a separate ESP32. Ensure the RA-02 antenna is attached and both devices use matching radio settings.
4. Test with the devices a short, controlled distance apart. Confirm that a transmitter event appears on the receiver serial output.
5. Connect receiver USB to local dashboard. Confirm a received event appears there.
6. Check GPS outdoors, SOS button, sensor candidate events, and SD files independently. Record actual results in the test report; do not infer success from code compilation.
7. Test packet loss, power cycling, duplicate events, range and interference in a safe controlled environment before making any performance claims.

## Event JSON format

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

`timestamp` is `null` until GPS date and time are valid. Latitude/longitude are `null` when there is no recent GPS fix. Event types currently used: `STATUS`, `SOS`, `IMPACT_CANDIDATE`, and `TILT_CANDIDATE`. Sensor candidates are not confirmed emergencies.

## Tests

From the project root:

```bat
python -m unittest discover -s tests -v
```

These are parser unit tests only. They do not test LoRa, GPS, SD, sensors, or marine performance.

## Known limitations

- No acknowledgement/retry protocol; a transmitted packet may be lost.
- No encryption or device authentication; do not send sensitive data.
- No certified emergency detection, distress routing, or guaranteed coverage.
- Impact/tilt thresholds are starting heuristics and need calibration.
- SD logging is best-effort; check card format, wiring, power and actual files.
- JSON message escaping is intended for the simple messages used by the sketch; extend safely if arbitrary user text is added.
- A shared default node ID must be changed if multiple vessel transmitters are deployed.
- The code is an MVP starting point and requires hardware validation and review.

## Suggested demo script

1. Show the dashboard in demo mode and explicitly label the map/events as simulated.
2. Show receiver boot output in Serial Monitor.
3. Press the transmitter SOS button and show the payload on receiver serial/dashboard.
4. Show GPS-valid vs no-fix behavior outdoors/indoors.
5. Show SD log files after powering down safely.
6. Explain that the prototype is not a replacement for certified maritime emergency systems.

## Submission status checklist

- [ ] Python dashboard starts successfully on the target machine.
- [ ] Unit tests pass.
- [ ] Both firmware sketches compile for the selected board.
- [ ] LoRa packet verified between the two physical nodes.
- [ ] GPS fix and coordinate values independently verified.
- [ ] SOS button event verified.
- [ ] MPU6050 candidate event tested and threshold documented.
- [ ] SD event logs verified after reboot.
- [ ] Local dashboard receives a physical receiver packet.
- [ ] Frequency/power compliance checked for the actual deployment.

Check only the items you have personally verified.
