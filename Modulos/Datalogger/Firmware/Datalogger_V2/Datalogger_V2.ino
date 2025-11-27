#include <WiFi.h>
#include <PubSubClient.h>
#include "Adafruit_INA3221.h"
#include <Wire.h>

// Configuración WiFi
const char* ssid = "RED2";              // Cambia esto por tu nombre de red WiFi
const char* password = "AleyVale2505";  // Cambia esto por tu contraseña WiFi

// Configuración MQTT
const char* mqtt_server = "192.168.1.10";  // Cambia esto por la IP de tu computadora donde corre el broker
const int mqtt_port = 1883;
const char* mqtt_topic = "esp32/sensors";

// Variables de sensores
float ch1 = 0;
float ch2 = 0;
float bat_1 = 0;
float temp_1 = 0;
float temp_2 = 0;
float bat_2 = 0;
float temp_amb = 0;
float hum_amb = 0;
float bat_3 = 0;
String inas = "";
String message = "";

// Intervalo de tiempo entre lecturas (en milisegundos)
const long interval = 1000;
unsigned long previousMillis = 0;

// Inicializar el cliente WiFi y MQTT
WiFiClient espClient;
PubSubClient client(espClient);

//Creamos los objetos de los sensores
Adafruit_INA3221 ina_a;
Adafruit_INA3221 ina_b;

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Conectando a ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi conectado");
  Serial.println("Dirección IP: ");
  Serial.println(WiFi.localIP());
}

void reconnect() {
  // Bucle hasta que estemos reconectados
  while (!client.connected()) {
    Serial.print("Intentando conexión MQTT...");
    // Crear un ID de cliente aleatorio
    String clientId = "ESP32Client-";
    clientId += String(random(0xffff), HEX);

    // Intentar conectar
    if (client.connect(clientId.c_str())) {
      Serial.println("conectado");
    } else {
      Serial.print("falló, rc=");
      Serial.print(client.state());
      Serial.println(" intentando de nuevo en 5 segundos");
      delay(5000);
    }
  }
}

void getVoltage() {
  ch1 = ina_a.getBusVoltage(0);
  ch2 = ina_a.getBusVoltage(1);
  ch3 = ina_a.getBusVoltage(2);
  ch4 = ina_b.getBusVoltage(0);
  ch5 = ina_b.getBusVoltage(1);
  ch6 = ina_b.getBusVoltage(2);
  /*
  Serial.println("ch1: " + String(ch1));
  Serial.println("ch2: " + String(ch2));
  Serial.println("ch3: " + String(ch3));
  Serial.println("ch4: " + String(ch4));
  Serial.println("ch5: " + String(ch5));
  Serial.println("ch6: " + String(ch6));
  Serial.println("");
*/
   inas = String(ch1, 4) + "," + String(ch2, 4) + "," + String(ch3, 4) + "," + String(ch4, 4) + "," + String(ch5, 4) + "," + String(ch6, 4);

  
}

void setup() {
  // Iniciando servicios de la ESP32
  Serial.begin(115200);
  Wire.begin();
  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);

  // Configuración de INA's
  if (!ina_a.begin(0x40, &Wire)) {
    Serial.println("sensor A exit: 1");
    while (1)
      delay(10);
  }
  Serial.println("sensor A exit: 0");

  if (!ina_b.begin(0x41, &Wire)) {
    Serial.println("sensor B exit: 1");
    while (1)
      delay(10);
  }
  Serial.println("sensor B exit: 0");

  ina_a.setAveragingMode(INA3221_AVG_128_SAMPLES);
  ina_b.setAveragingMode(INA3221_AVG_128_SAMPLES);


  for (uint8_t i = 0; i < 3; i++) {
    ina_a.setShuntResistance(i, 0.005);
    ina_b.setShuntResistance(i, 0.005);
  }

  ina_a.setPowerValidLimits(3.0, 15.0);
  ina_b.setPowerValidLimits(3.0, 15.0);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  unsigned long currentMillis = millis();

  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;

    getVoltage();
    message = inas;

    Serial.print("Publicando mensaje: ");
    Serial.println(message);

    // Publicar en el tema MQTT
    client.publish(mqtt_topic, message.c_str());
  }
}