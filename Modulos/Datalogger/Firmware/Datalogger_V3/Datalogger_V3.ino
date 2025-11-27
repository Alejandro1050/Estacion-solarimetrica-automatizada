#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <DFRobot_ADS1115.h>
#include <LiquidCrystal_I2C.h>

// Configuración WiFi
const char* ssid = "RED2_4";              
const char* password = "AleyVale2505";
//const char* ssid = "Cisco02965";              
//const char* password = "datos_manda";  

// Configuración MQTT
const char* mqtt_server = "192.168.10.205";  
const int mqtt_port = 1883;
const char* mqtt_topic = "esp32/sensors";

// Definición de pines UART para HC-12
#define HC12_RX_PIN 3  // Conectar TX del HC-12
#define HC12_TX_PIN 2  // Conectar RX del HC-12

HardwareSerial hc(1);  // Usamos UART1 (UART0 está ocupado por USB)
LiquidCrystal_I2C lcd(0x27, 20, 4); 
DFRobot_ADS1115 ads(&Wire);

// Variables para control de lapsos
unsigned long lastDisplayTime = 0;
int displayPhase = 0;  // 0: voltaje/batería, 1: datos1, 2: datos2


// Variables de sensores
float bat_1 = 0;

String data_0;
String data_1;
String message = "";

const int bat_pin = 5;      // Pin ADC
const float R1 = 100000.0;  // Resistencia superior (100kΩ)
const float R2 = 220000.0;  // Resistencia inferior (220kΩ)

// Intervalo de tiempo entre lecturas (en milisegundos)
const long interval = 500;
unsigned long previousMillis = 0;

// Inicializar el cliente WiFi y MQTT
WiFiClient espClient;
PubSubClient client(espClient);


void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Conectando a ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    lcd.setCursor(0, 0);
    lcd.print("Conectando...");
  }

  Serial.println("");
  Serial.println("WiFi conectado");
  Serial.println("Dirección IP: ");
  Serial.println(WiFi.localIP());

  delay(1500);
}

void reconnect() {
  // Bucle hasta que estemos reconectados
  lcd.clear();

  while (!client.connected()) {
    Serial.print("Intentando conexión MQTT...");
    lcd.setCursor(0, 0);
    lcd.print("MQTT...");
    // Crear un ID de cliente aleatorio
    String clientId = "ESP32Client-";
    clientId += String(random(0xffff), HEX);

    // Intentar conectar
    if (client.connect(clientId.c_str())) {
      Serial.println("conectado");
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("MQTT");
      lcd.setCursor(0, 1);
      lcd.print("CONECTADO!");
      delay(1500);
    } else {
      Serial.print("falló, rc=");
      Serial.print(client.state());
      Serial.println(" intentando de nuevo en 5 segundos");
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Error MQTT");
      lcd.setCursor(0, 1);
      lcd.print(client.state());
      delay(5000);
    }
  }
}

String getVoltage() {

  if (ads.checkADS1115()) {
    int16_t ch1, ch2;
    ch1 = ads.readVoltage(0);
    ch2 = ads.readVoltage(1);

    String voltage = String(ch1) + "," + String(ch2);
    return voltage;
  } else {

    return ("Nan, Nan");
  }
}

String bat_level(int adc) {
  float voltage = (adc * (3.3 / 4095.0) - 0.20) * ((R1 + R2) / R2);

  return String(voltage);
}

String get_data(int id) {
  // Limpiar el buffer serial
  while(hc.available() > 0) {
    hc.read();
  }
  
  // Enviar ID con salto de línea
  hc.println(id);

  // Esperar respuesta con timeout
  unsigned long startTime = millis();
  while (millis() - startTime < 1000) {  // Timeout aumentado a 1 segundo
    if (hc.available() > 0) {
      String data = hc.readStringUntil('\n');
      data.trim();
      if(data.length() > 0) {  // Asegurarse de que no está vacío
        return data;
      }
    }
  }
  return "Nan, Nan, Nan";
}

String get_data_1(int id) {
  // Limpiar el buffer serial
  while(hc.available() > 0) {
    hc.read();
  }
  
  // Enviar ID con salto de línea
  hc.println(id);

  // Esperar respuesta con timeout
  unsigned long startTime = millis();
  while (millis() - startTime < 1000) {  // Timeout aumentado a 1 segundo
    if (hc.available() > 0) {
      String data = hc.readStringUntil('\n');
      data.trim();
      if(data.length() > 0) {  // Asegurarse de que no está vacío
        return data;
      }
    }
  }
  return "Nan, Nan, Nan";
}

void displayDataOnLCD() {
  unsigned long currentMillis = millis();

  // Cambiar fase cada 5 segundos
  if (currentMillis - lastDisplayTime >= 5000) {
    lastDisplayTime = currentMillis;
    displayPhase = (displayPhase + 1) % 3;
    lcd.clear();
  }

  // Mostrar datos según la fase actual
  switch (displayPhase) {
    case 0:  // Mostrar voltaje y nivel de batería local
      {
        int sensorValue = analogRead(bat_pin);
        String voltageStr = getVoltage();
        String batteryStr = bat_level(sensorValue);

        lcd.setCursor(0, 0);
        lcd.print("Voltaje: " + voltageStr);
        lcd.setCursor(0, 1);
        lcd.print("Bateria: " + batteryStr);
      }
      break;

    case 1:  // Mostrar datos del primer dispositivo remoto
      {
        String remoteData1 = get_data(1);
        // Asumiendo formato "temp1,temp2,bateria"
        int comma1 = remoteData1.indexOf(',');
        int comma2 = remoteData1.indexOf(',', comma1 + 1);

        String temp1 = remoteData1.substring(0, comma1);
        String temp2 = remoteData1.substring(comma1 + 1, comma2);
        String batRemote = remoteData1.substring(comma2 + 1);

        lcd.setCursor(0, 0);
        lcd.print("Temp1: " + temp1 + "C");
        lcd.setCursor(0, 1);
        lcd.print("Temp2: " + temp2 + "C");
        lcd.setCursor(0, 2);
        lcd.print("BatR1: " + batRemote + "V");
      }
      break;

    case 2:  // Mostrar datos del segundo dispositivo remoto
      {
        String remoteData2 = get_data(2);
        // Asumiendo formato "temperatura,humedad,bateria"
        int comma1 = remoteData2.indexOf(',');
        int comma2 = remoteData2.indexOf(',', comma1 + 1);

        String temp = remoteData2.substring(0, comma1);
        String hum = remoteData2.substring(comma1 + 1, comma2);
        String batRemote = remoteData2.substring(comma2 + 1);

        lcd.setCursor(0, 0);
        lcd.print("Temp: " + temp + "C");
        lcd.setCursor(0, 1);
        lcd.print("Hum: " + hum + "%");
        lcd.setCursor(0, 2);
        lcd.print("BatR2: " + batRemote + "V");
      }
      break;
  }
}

void setup() {
  // Iniciando servicios de la ESP32
  Serial.begin(115200);

  lcd.init();
  lcd.backlight();

  hc.begin(9600, SERIAL_8N1, HC12_RX_PIN, HC12_TX_PIN);
  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("MQTT Listo!");

  ads.setAddr_ADS1115(0x48);      // 0x48
  ads.setGain(eGAIN_TWO);         // 2x gain
  ads.setMode(eMODE_SINGLE);      // single-shot mode
  ads.setRate(eRATE_128);         // 128SPS (default)
  ads.setOSMode(eOSMODE_SINGLE);  // Set to start a single-conversion
  ads.init();

  lcd.clear();
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  unsigned long currentMillis = millis();

  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;

    int sensorValue = analogRead(1);

    String termocuplas = get_data(1);
    delay(200);
    String ambiente = get_data_1(2);
    
    message = getVoltage() + "," + bat_level(sensorValue) + "," + termocuplas + "," + ambiente;

    Serial.print("Publicando mensaje: ");
    Serial.println(message);

    // Publicar en el tema MQTT
    client.publish(mqtt_topic, message.c_str());
  }
  displayDataOnLCD();
}