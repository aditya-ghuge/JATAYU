/*
 * ==============================================================================
 * ResQRoute AI - ESP32 Telemetry Node (Arduino C++)
 * ==============================================================================
 * Reads DHT22 / DS18B20 (Temperature), MQ-2 (Smoke/Gas), and IR Flame Sensor.
 * Transmits JSON telemetry packet over WiFi HTTP POST to the FastAPI backend.
 *
 * Hardware Wiring:
 *   - DHT22 (Temperature) -> GPIO 4
 *   - MQ-2 Analog (Gas)   -> GPIO 34 (ADC1)
 *   - Flame Digital/ADC   -> GPIO 35 (ADC1)
 * ==============================================================================
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>

// WiFi Configuration
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Backend API Configuration
const char* SERVER_URL    = "http://192.168.1.100:8000/telemetry"; // Change to your Server IP
const char* ZONE_ID       = "C1"; // Set specific Zone ID for this hardware node

// Pin Definitions
#define DHTPIN 4
#define DHTTYPE DHT22
#define MQ2_PIN 34
#define FLAME_PIN 35

DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(115200);
  delay(1000);

  dht.begin();
  pinMode(MQ2_PIN, INPUT);
  pinMode(FLAME_PIN, INPUT);

  // Connect to WiFi
  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi Connected! IP Address: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    // 1. Read Sensors
    float temperature = dht.readTemperature(); // Celsius
    int raw_gas = analogRead(MQ2_PIN);         // 0 - 4095 on ESP32
    int raw_flame = analogRead(FLAME_PIN);     // 0 - 4095

    // Normalize gas ADC to estimated ppm (example mapping)
    float gas_ppm = (raw_gas / 4095.0) * 500.0;

    // Normalize flame (Active LOW or normalized index)
    float flame_index = (4095.0 - raw_flame) / 4095.0; // 1.0 = intense flame, 0.0 = none
    if (flame_index < 0.2) flame_index = 0.0;

    // Handle sensor read failures
    const char* status = "ONLINE";
    if (isnan(temperature)) {
      temperature = 22.0;
      status = "DEGRADED";
    }

    // 2. Build JSON Payload
    String jsonPayload = "{";
    jsonPayload += "\"zone_id\":\"" + String(ZONE_ID) + "\",";
    jsonPayload += "\"temperature\":" + String(temperature, 1) + ",";
    jsonPayload += "\"gas\":" + String(gas_ppm, 1) + ",";
    jsonPayload += "\"flame\":" + String(flame_index, 2) + ",";
    jsonPayload += "\"status\":\"" + String(status) + "\"";
    jsonPayload += "}";

    Serial.print("Sending Payload: ");
    Serial.println(jsonPayload);

    // 3. Send HTTP POST Request
    HTTPClient http;
    http.begin(SERVER_URL);
    http.addHeader("Content-Type", "application/json");

    int httpResponseCode = http.POST(jsonPayload);

    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.print("HTTP Response Code: ");
      Serial.println(httpResponseCode);
      Serial.println("Response: " + response);
    } else {
      Serial.print("Error on sending POST: ");
      Serial.println(httpResponseCode);
    }

    http.end();
  } else {
    Serial.println("WiFi Disconnected. Reconnecting...");
    WiFi.reconnect();
  }

  // Send update every 2 seconds
  delay(2000);
}
