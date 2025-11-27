#include "max6675.h"
#include "SoftwareSerial.h"

SoftwareSerial hc(3, 4);  // (Tx del HC-12, Rx del HC-12)

int thermoDO = 10;
int thermoCS = 11;
int thermoCLK = 12;

int thermoDO_1 = 7;
int thermoCS_1 = 8;
int thermoCLK_1 = 9;

MAX6675 thermocouple(thermoCLK, thermoCS, thermoDO);
MAX6675 thermocouple_1(thermoCLK_1, thermoCS_1, thermoDO_1);

float temp_0 = 0.0;
float temp_1 = 0.0;
float bat = 0.0;

const int bat_pin = A6;
int sensorValue = 0;
const float R1 = 1000.0;
const float R2 = 1000.0;

String bat_level(int adc) {
  float voltage = (adc * (5.0 / 1023.0)) * ((R1 + R2) / R2);

  return String(voltage);
}

void setup() {
  Serial.begin(9600);
  hc.begin(9600);
  analogReference(DEFAULT);
  Serial.println("Sistema iniciado");
}

void loop() {

  // Comprobar si hay datos recibidos
  if (hc.available() > 0) {
    String input = hc.readStringUntil('\n');  // Leer hasta fin de línea
    //char input = hc.read();
    input.trim();  // Eliminar espacios o retornos de carro

    if (input == "1") {  // ID del receptor
      temp_0 = thermocouple.readCelsius();
      temp_1 = thermocouple_1.readCelsius();

      sensorValue = analogRead(bat_pin);
      String response = String(temp_0, 2) + "," + String(temp_1, 2) + "," + String(bat_level(sensorValue)) + "\n";
      hc.print(response);
      Serial.print("Enviado: ");
      Serial.print(response);
    }
  }
}