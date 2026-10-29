/*
  SeaSafe vessel transmitter — ESP32 + RA-02 (SX1278) + GPS + MPU6050 + microSD.
  Example wiring is in docs/WIRING.md. Validate pins and 3.3V logic before powering.
  This is source code for integration; physical radio/sensor operation is NOT verified.
*/
#include <SPI.h>
#include <LoRa.h>
#include <Wire.h>
#include <TinyGPSPlus.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <SD.h>
#include <time.h>

// RA-02 / LoRa SPI (VSPI)
constexpr int LORA_SCK=18, LORA_MISO=19, LORA_MOSI=23, LORA_CS=27, LORA_RST=14, LORA_DIO0=26;
// GPS on UART2
constexpr int GPS_RX=32, GPS_TX=33;
// microSD on separate SPI bus (HSPI)
constexpr int SD_SCK=5, SD_MISO=16, SD_MOSI=17, SD_CS=13;
constexpr int SOS_PIN=25;
constexpr float LORA_FREQUENCY=433E6; // Use only a locally permitted frequency/power.
constexpr float IMPACT_THRESHOLD=22.0; // m/s^2; tune only after controlled testing.
constexpr float TILT_THRESHOLD_DEG=55.0;

SPIClass sdSPI(HSPI);
TinyGPSPlus gps;
HardwareSerial GPSSerial(2);
Adafruit_MPU6050 mpu;
bool mpuReady=false, sdReady=false, loraReady=false;
String nodeId="VESSEL-01";
unsigned long lastStatus=0, lastSensor=0, eventCounter=0;
bool previousSos=false;

String makeEventId() {
  char buf[32];
  snprintf(buf, sizeof(buf), "%s-%lu", nodeId.c_str(), ++eventCounter);
  return String(buf);
}

String isoTimestamp() {
  if (!gps.date.isValid() || !gps.time.isValid()) return "null";
  char buf[32];
  snprintf(buf, sizeof(buf), "\"%04d-%02d-%02dT%02d:%02d:%02dZ\"",
    gps.date.year(), gps.date.month(), gps.date.day(),
    gps.time.hour(), gps.time.minute(), gps.time.second());
  return String(buf);
}

void appendLog(const String &line) {
  if (!sdReady) return;
  File f=SD.open("/seasafe_events.jsonl", FILE_APPEND);
  if (f) { f.println(line); f.close(); }
}

void emitEvent(const char* type, const char* message) {
  bool gpsValid=gps.location.isValid() && gps.location.age() < 5000;
  String lat=gpsValid ? String(gps.location.lat(), 6) : "null";
  String lon=gpsValid ? String(gps.location.lng(), 6) : "null";
  String ts=isoTimestamp();
  String id=makeEventId();
  String json="{\"node_id\":\""+nodeId+"\",\"event_id\":\""+id+
    "\",\"event_type\":\""+String(type)+"\",\"timestamp\":"+ts+
    ",\"latitude\":"+lat+",\"longitude\":"+lon+
    ",\"gps_valid\":"+(gpsValid ? "true":"false")+
    ",\"test_mode\":false,\"message\":\""+String(message)+"\"}";
  Serial.println(json);             // USB serial output for local dashboard
  if (loraReady) { LoRa.beginPacket(); LoRa.print(json); LoRa.endPacket(); }
  appendLog(json);                  // local black-box event record when SD works
}

void setup() {
  Serial.begin(115200);
  pinMode(SOS_PIN, INPUT_PULLUP);
  GPSSerial.begin(9600, SERIAL_8N1, GPS_RX, GPS_TX);
  Wire.begin(21,22);
  mpuReady=mpu.begin();
  if (mpuReady) {
    mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
    mpu.setGyroRange(MPU6050_RANGE_500_DEG);
    mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
  }

  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_CS);
  LoRa.setPins(LORA_CS, LORA_RST, LORA_DIO0);
  loraReady=LoRa.begin(LORA_FREQUENCY);
  if (loraReady) LoRa.setTxPower(14);

  sdSPI.begin(SD_SCK, SD_MISO, SD_MOSI, SD_CS);
  sdReady=SD.begin(SD_CS, sdSPI);

  Serial.printf("{\"node_id\":\"%s\",\"event_id\":\"BOOT\",\"event_type\":\"STATUS\",\"timestamp\":null,\"gps_valid\":false,\"test_mode\":false,\"message\":\"boot; lora=%s mpu=%s sd=%s\"}\n",
    nodeId.c_str(), loraReady?"ready":"failed", mpuReady?"ready":"failed", sdReady?"ready":"failed");
}

void loop() {
  while (GPSSerial.available()) gps.encode(GPSSerial.read());

  bool sos=(digitalRead(SOS_PIN)==LOW);
  if (sos && !previousSos) emitEvent("SOS", "SOS button pressed");
  previousSos=sos;

  if (mpuReady && millis()-lastSensor >= 250) {
    lastSensor=millis();
    sensors_event_t a,g,temp;
    mpu.getEvent(&a,&g,&temp);
    float magnitude=sqrt(a.acceleration.x*a.acceleration.x +
                         a.acceleration.y*a.acceleration.y +
                         a.acceleration.z*a.acceleration.z);
    float tilt=atan2(sqrt(a.acceleration.x*a.acceleration.x + a.acceleration.y*a.acceleration.y),
                     fabs(a.acceleration.z))*180.0/PI;
    if (magnitude > IMPACT_THRESHOLD) emitEvent("IMPACT_CANDIDATE", "Acceleration threshold exceeded; verify manually");
    else if (tilt > TILT_THRESHOLD_DEG) emitEvent("TILT_CANDIDATE", "Tilt threshold exceeded; verify manually");
  }

  if (millis()-lastStatus >= 15000) {
    lastStatus=millis();
    emitEvent("STATUS", "Vessel node heartbeat");
  }
  delay(5);
}
