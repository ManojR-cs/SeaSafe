# SeaSafe Test Report

Date:
Tester:
ESP32 board model(s):
RA-02 module version:
Arduino core / library versions:
Location and test conditions:

| Test | Expected result | Actual result / evidence | Pass/Fail |
|---|---|---|---|
| Dashboard starts | Local Streamlit page loads | | |
| Unit tests | All parser tests pass | | |
| Receiver initialization | Startup JSON reports LoRa init result | | |
| Radio packet | Receiver prints transmitter event | | |
| GPS fix | Valid coordinates outdoors | | |
| SOS button | SOS event emitted once per press | | |
| MPU6050 | Candidate event under controlled movement | | |
| SD logging | JSONL file persists after reboot | | |
| Dashboard live mode | Physical received event appears | | |

Do not write “pass” without observed evidence. Attach photos, serial logs or test output where possible.
