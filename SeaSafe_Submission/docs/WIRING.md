# Wiring reference

These are proposed pin assignments for a classic ESP32 DevKit using an RA-02/SX1278 module. Some ESP32-S3 boards expose different pins or reserve pins internally; check the exact board pinout before wiring. Both RA-02 and ESP32 use 3.3 V logic. **Never connect RA-02 to 5 V.** Power and antenna requirements matter.

## Vessel transmitter

| Component | Module pin | ESP32 pin |
|---|---|---:|
| RA-02 | VCC | 3V3 (stable supply capable of radio current peaks) |
| RA-02 | GND | GND |
| RA-02 | SCK | GPIO 18 |
| RA-02 | MISO | GPIO 19 |
| RA-02 | MOSI | GPIO 23 |
| RA-02 | NSS/CS | GPIO 27 |
| RA-02 | RESET | GPIO 14 |
| RA-02 | DIO0 | GPIO 26 |
| GPS UART | TX | GPIO 32 (ESP32 RX) |
| GPS UART | RX | GPIO 33 (ESP32 TX; optional for many GPS modules) |
| MPU6050 | SDA | GPIO 21 |
| MPU6050 | SCL | GPIO 22 |
| SOS button | one terminal | GPIO 25 |
| SOS button | other terminal | GND |
| microSD SPI | SCK | GPIO 5 |
| microSD SPI | MISO | GPIO 16 |
| microSD SPI | MOSI | GPIO 17 |
| microSD SPI | CS | GPIO 13 |
| microSD | VCC/GND | Match module requirements / common GND |

## Shore receiver

Wire the RA-02 to the same LoRa pins above. The receiver's microSD uses the same SD pin assignments if fitted. Connect receiver ESP32 USB to the computer running the local Streamlit dashboard.

## Safety and integration notes

- Verify module labels and board pinout; don't rely on physical pin order.
- Use a suitable 3.3 V regulator and short wires. RA-02 transmit current peaks can reset an underpowered ESP32.
- Attach the correct antenna before transmitting. Do not transmit into an unterminated RF output.
- Both radios must use the same frequency, bandwidth, spreading factor, coding rate and sync word. The sketches use the LoRa library defaults on both ends.
- The sketches use 433 MHz as a configurable example only. Confirm India's current WPC/DoT rules, permitted band, power and antenna conditions before transmitting; do not assume 433 MHz is automatically permitted for this setup.
- GPS needs a view of the sky and may report no fix indoors. Invalid GPS is explicitly represented.
- MPU6050 impact/tilt thresholds are heuristic candidates, not a certified man-overboard or distress detector. They need controlled calibration.
- A button press and radio delivery are not guaranteed emergency communications. Keep ordinary marine safety equipment and established distress channels.
