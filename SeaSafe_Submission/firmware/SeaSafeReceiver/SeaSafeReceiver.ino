/*
  SeaSafe shore receiver — ESP32 + RA-02 (SX1278) + optional microSD.
  Prints one JSON event per received LoRa packet over USB serial at 115200 baud.
  Hardware reception is NOT verified; test only with a permitted frequency and range.
*/
#include <SPI.h>
#include <LoRa.h>
#include <SD.h>

constexpr int LORA_SCK=18, LORA_MISO=19, LORA_MOSI=23, LORA_CS=27, LORA_RST=14, LORA_DIO0=26;
constexpr int SD_SCK=5, SD_MISO=16, SD_MOSI=17, SD_CS=13;
constexpr float LORA_FREQUENCY=433E6; // Confirm local rules before use.

SPIClass sdSPI(HSPI);
bool loraReady=false, sdReady=false;
unsigned long receivedCount=0;

void setup() {
  Serial.begin(115200);
  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_CS);
  LoRa.setPins(LORA_CS, LORA_RST, LORA_DIO0);
  loraReady=LoRa.begin(LORA_FREQUENCY);

  sdSPI.begin(SD_SCK, SD_MISO, SD_MOSI, SD_CS);
  sdReady=SD.begin(SD_CS, sdSPI);

  Serial.printf("{\"node_id\":\"SHORE-01\",\"event_id\":\"BOOT\",\"event_type\":\"STATUS\",\"timestamp\":null,\"gps_valid\":false,\"test_mode\":false,\"message\":\"receiver boot; lora=%s sd=%s\"}\n",
    loraReady?"ready":"failed", sdReady?"ready":"failed");
  if (!loraReady) Serial.println("{\"node_id\":\"SHORE-01\",\"event_id\":\"LORA-ERROR\",\"event_type\":\"STATUS\",\"timestamp\":null,\"gps_valid\":false,\"test_mode\":false,\"message\":\"LoRa.begin failed; check wiring, module and frequency\"}");
}

void loop() {
  if (!loraReady) { delay(1000); return; }
  int packetSize=LoRa.parsePacket();
  if (!packetSize) return;

  String payload;
  while (LoRa.available()) payload += (char)LoRa.read();
  payload.trim();
  if (payload.length()==0) return;

  // Pass through only JSON objects. Dashboard performs full validation.
  if (!payload.startsWith("{") || !payload.endsWith("}")) {
    Serial.println("{\"node_id\":\"SHORE-01\",\"event_id\":\"RX-INVALID\",\"event_type\":\"STATUS\",\"timestamp\":null,\"gps_valid\":false,\"test_mode\":false,\"message\":\"Received non-JSON LoRa payload\"}");
    return;
  }

  Serial.println(payload);
  receivedCount++;
  if (sdReady) {
    File f=SD.open("/seasafe_received.jsonl", FILE_APPEND);
    if (f) {
      f.print("{\"received_count\":"); f.print(receivedCount);
      f.print(",\"rssi_dbm\":"); f.print(LoRa.packetRssi());
      f.print(",\"snr_db\":"); f.print(LoRa.packetSnr());
      f.print(",\"payload\":"); f.print("\"");
      for (size_t i=0;i<payload.length();i++) {
        char c=payload[i]; if (c=='\"' || c=='\\') f.print('\\');
        if (c=='\n' || c=='\r') continue;
        f.print(c);
      }
      f.println("\"}"); f.close();
    }
  }
}
