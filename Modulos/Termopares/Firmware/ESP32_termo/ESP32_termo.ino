#include "max6675.h"

// Pines para termocuplas en ESP32-C3
const int thermoDO = 2;   // Pin 2
const int thermoCS = 3;   // Pin 3
const int thermoCLK = 4;  // Pin 4

const int thermoDO_1 = 5;   // Pin 5
const int thermoCS_1 = 6;   // Pin 6
const int thermoCLK_1 = 7;  // Pin 7

MAX6675 thermocouple(thermoCLK, thermoCS, thermoDO);
MAX6675 thermocouple_1(thermoCLK_1, thermoCS_1, thermoDO_1);

// Configuración UART para HC-12
HardwareSerial hc(1);
#define HC12_RX_PIN 9  // Conectar TX del HC-12 aquí
#define HC12_TX_PIN 8  // Conectar RX del HC-12 aquí

const int bat_pin = A1;
int sensorValue = 0;
const float R1 = 10000.0;
const float R2 = 22000.0;

float temp_0 = 0.0;
float temp_1 = 0.0;

String bat_level(int adc) {
  float voltage = ((adc * (3.3 / 4095.0)) * ((R1 + R2) / R2)) - 0.60;

  return String(voltage);
}

void setup() {
  Serial.begin(115200);
  Serial.println("Termocuplas iniciadas");

  // Inicializar UART para HC-12
  hc.begin(9600, SERIAL_8N1, HC12_RX_PIN, HC12_TX_PIN);

  // Dar tiempo a las termocuplas para estabilizarse
  delay(1000);
}

void loop() {

  if (hc.available() > 0) {
    char input = hc.read();

    if (input == '1') {
      // Leer temperaturas
      temp_0 = thermocouple.readCelsius();
      temp_1 = thermocouple_1.readCelsius();
      //temp_0 = 60.5;
      //temp_1 = 66.6;

      if (isnan(temp_0)) temp_0 = -999.99;
      if (isnan(temp_1)) temp_1 = -999.99;

      sensorValue = analogRead(bat_pin);

      String response = String(temp_0) + "," + String(temp_1) + "," + String(bat_level(sensorValue)) + "\n";
      hc.println(response);

      Serial.print("Temperaturas enviadas: ");
      Serial.println(response);
    }
  }
}