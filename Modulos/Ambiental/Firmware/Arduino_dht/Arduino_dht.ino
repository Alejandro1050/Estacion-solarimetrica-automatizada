#include <SoftwareSerial.h>
#include <DHT.h>

#define DHTPIN 13  // Pin para el DHT11
#define DHTTYPE DHT11

SoftwareSerial hc12(3, 4);  // RX, TX (3=TX, 4=RX)
DHT dht(DHTPIN, DHTTYPE);

const int bat_pin = A6;  // Pin ADC
const float R1 = 100000.0;  // Resistencia superior (100kΩ)
const float R2 = 100000.0;  // Resistencia inferior (220kΩ)

String bat_level(int adc) {
  float voltage = adc * (5.0 / 1023.0) * ((R1 + R2) / R2);

  return String(voltage);
}

void setup() {
  Serial.begin(9600);
  hc12.begin(9600);
  dht.begin();
  Serial.println("Sistema iniciado");
}

void loop() {
  if (hc12.available() > 0) {
    String input = hc12.readStringUntil('\n');
    input.trim();

    if (input == "2") {  // ID de este dispositivo
      float h = dht.readHumidity();
      float t = dht.readTemperature();
      int sensorValue = analogRead(bat_pin);

      String data = String(t) + "," + String(h) + + "," + String(bat_level(sensorValue)) + ('\n');
      hc12.println(data);
      Serial.println(data);
    }
  }
}