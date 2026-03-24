#include <WiFi.h>
#include <WebServer.h>
#include <DHT.h>

#define DHTPIN 4
#define DHTTYPE DHT11

#define SOIL_PIN 35
#define SOIL_POWER 25

const char* ssid = "Dhinnu";
const char* password = "987654321";

WebServer server(80);
DHT dht(DHTPIN, DHTTYPE);

// Calibration
int dryValue = 3200;
int wetValue = 1200;

float temp, hum;
int soilPercent;

void readSensors() {
  temp = dht.readTemperature();
  hum = dht.readHumidity();

  if (isnan(temp) || isnan(hum)) {
    temp = 0;
    hum = 0;
  }

  digitalWrite(SOIL_POWER, HIGH);
  delay(1000);

  int soilRaw = 0;
  for (int i = 0; i < 5; i++) {
    soilRaw += analogRead(SOIL_PIN);
    delay(100);
  }
  soilRaw /= 5;

  digitalWrite(SOIL_POWER, LOW);

  soilPercent = map(soilRaw, dryValue, wetValue, 0, 100);
  soilPercent = constrain(soilPercent, 0, 100);
}

void handleData() {
  readSensors();

  String json = "{";
  json += "\"temp\":" + String(temp) + ",";
  json += "\"humidity\":" + String(hum) + ",";
  json += "\"soil\":" + String(soilPercent);
  json += "}";

  server.send(200, "application/json", json);
}

void setup() {
  Serial.begin(115200);
  dht.begin();

  pinMode(SOIL_POWER, OUTPUT);
  digitalWrite(SOIL_POWER, LOW);

  WiFi.begin(ssid, password);

  Serial.print("Connecting...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nConnected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());

  server.on("/data", handleData);
  server.begin();
}

void loop() {
  server.handleClient();
}