#include <Wire.h>
#include "Adafruit_SHT31.h"

Adafruit_SHT31 sht31 = Adafruit_SHT31();

// Configuración UART para HC-12
HardwareSerial hc(1);
#define HC12_RX_PIN 4  // Conectar TX del HC-12 aquí
#define HC12_TX_PIN 3  // Conectar RX del HC-12 aquí

const int bat_pin = A2;
int sensorValue = 0;
const float R1 = 10000.0;
const float R2 = 22000.0;

float temp = 0.0;
float hum = 0.0;
bool error = false;

String bat_level(int adc) {
  float voltage = ((adc * (3.3 / 4095.0)) * ((R1 + R2) / R2)) - 0.68;
  return String(voltage);
}

void setup() {
  Serial.begin(115200);
  Serial.println("Ambiental iniciado");

  // Inicializar UART para HC-12
  hc.begin(9600, SERIAL_8N1, HC12_RX_PIN, HC12_TX_PIN);

  if (!sht31.begin(0x44)) {  // Set to 0x45 for alternate i2c addr
    Serial.println("Sensor Error!");
    error = true;
  }

  // Lectura inicial de batería
  sensorValue = analogRead(bat_pin);
  
  delay(1000);
}

void loop() {
  if (hc.available() > 0) {
    char input = hc.read();

    Serial.print("Comando recibido: ");
    Serial.println(input);

    if (input == '2') {
      if (!error) {
        temp = sht31.readTemperature();
        hum = sht31.readHumidity();

        // Corrección: Verificación correcta de lecturas inválidas
        bool tempError = isnan(temp);
        bool humError = isnan(hum);
        
        // Actualizar lectura de batería
        sensorValue = analogRead(bat_pin);

        String response = "";
        if (tempError || humError) {
          // Si hay error en alguna lectura, enviar "nan"
          response = "nan,nan," + String(bat_level(sensorValue)) + "\n";
        } else {
          // Si ambas lecturas son válidas
          response = String(temp, 2) + "," + String(hum, 2) + "," + String(bat_level(sensorValue)) + "\n";
        }
        
        hc.println(response);
        Serial.print("Datos enviados: ");
        Serial.println(response);
      } else {
        // En caso de error de inicialización del sensor
        sensorValue = analogRead(bat_pin);
        String response = "nan,nan," + String(bat_level(sensorValue)) + "\n";
        hc.println(response);
        Serial.print("Datos enviados: ");
        Serial.println(response);
      }
    }
  }
  
  delay(100); // Pequeña pausa para evitar saturación
}