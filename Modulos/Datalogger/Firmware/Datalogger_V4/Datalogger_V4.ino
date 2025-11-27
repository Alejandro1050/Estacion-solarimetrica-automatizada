#include "FS.h"
#include "SD.h"
#include "SPI.h"
#include <Wire.h>
#include <Adafruit_ADS1X15.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include "RTClib.h"
#include <LiquidCrystal_I2C.h>

RTC_DS1307 rtc;

LiquidCrystal_I2C lcd(0x27, 16, 2);

// Configuración WiFi
const char* ssid = "LER";
const char* password = "datos_manda";

// Configuración MQTT
const char* mqtt_server = "192.168.1.3";
const int mqtt_port = 1883;
const char* mqtt_topic = "esp32/sensors";
const char* mqtt_command_topic = "esp32/commands";

// Definición de pines
#define HC12_RX_PIN 3  // Conectar TX del HC-12
#define HC12_TX_PIN 2  // Conectar RX del HC-12
#define SD_CS_PIN 7    // Pin Chip Select para la SD

HardwareSerial hc(1);  // UART1 para HC-12
Adafruit_ADS1115 ads;

// Variables para el manejo del tiempo
const long interval = 60000;
unsigned long previousMillis = 0;

// Variables de estado
bool SD_Error = false;
bool wifiConnected = false;
bool mqttConnected = false;
int connectionAttempts = 0;
File dataFile;

// Inicializar el cliente WiFi y MQTT
WiFiClient espClient;
PubSubClient client(espClient);

// Función para conectarse al Wifi
void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Conectando a: ");
  Serial.println(ssid);

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Conectando WiFi");
  lcd.setCursor(0, 1);
  lcd.print(ssid);

  // Configuración específica para ESP32-C3
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.setTxPower(WIFI_POWER_19_5dBm);  // Aumentar potencia de transmisión
  WiFi.setHostname("Datalogger-C3");

  // Limpiar configuración previa
  WiFi.disconnect(true);
  delay(2000);

  // Configurar parámetros WiFi específicos
  WiFi.setScanMethod(WIFI_ALL_CHANNEL_SCAN);
  WiFi.setSortMethod(WIFI_CONNECT_AP_BY_SIGNAL);

  Serial.println("Iniciando conexión...");
  WiFi.begin(ssid, password);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 25) {
    delay(1000);
    Serial.print("Intento ");
    Serial.print(attempts);
    Serial.print(" - Estado: ");
    Serial.println(WiFi.status());

    // Mostrar punto en LCD
    lcd.setCursor(attempts, 1);
    lcd.print(".");

    attempts++;

    // Reiniciar conexión después de 10 intentos
    if (attempts == 10) {
      Serial.println("Reiniciando conexión WiFi...");
      WiFi.disconnect();
      delay(1000);
      WiFi.begin(ssid, password);
    }
  }

  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    Serial.println("WiFi CONECTADO!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
    Serial.print("RSSI: ");
    Serial.println(WiFi.RSSI());

    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("WiFi Conectado");
    lcd.setCursor(0, 1);
    lcd.print("IP: ");
    lcd.print(WiFi.localIP());
  } else {
    wifiConnected = false;
    Serial.println("FALLA en conexión WiFi");
    Serial.print("Último estado: ");
    Serial.println(WiFi.status());

    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Error WiFi");
    lcd.setCursor(0, 1);
    lcd.print("Estado ");
    lcd.print(WiFi.status());
  }
  delay(2000);
}

void wifiDiagnostic() {
  Serial.println("\n=== DIAGNÓSTICO WiFi DETALLADO ===");

  // Verificar si el SSID está disponible
  Serial.println("Escaneando redes...");
  int n = WiFi.scanNetworks();
  Serial.print("Redes encontradas: ");
  Serial.println(n);

  bool networkFound = false;
  for (int i = 0; i < n; ++i) {
    Serial.print(i + 1);
    Serial.print(": ");
    Serial.print(WiFi.SSID(i));
    Serial.print(" (");
    Serial.print(WiFi.RSSI(i));
    Serial.print(" dBm) ");
    Serial.println((WiFi.encryptionType(i) == WIFI_AUTH_OPEN) ? "Abierta" : "Protegida");

    if (WiFi.SSID(i) == ssid) {
      networkFound = true;
      Serial.print("*** RED LER ENCONTRADA - Señal: ");
      Serial.print(WiFi.RSSI(i));
      Serial.println(" dBm ***");
    }
  }

  if (!networkFound) {
    Serial.println("*** ADVERTENCIA: Red LER no encontrada ***");
  }

  Serial.print("Estado WiFi: ");
  switch (WiFi.status()) {
    case WL_IDLE_STATUS: Serial.println("WL_IDLE_STATUS (0)"); break;
    case WL_NO_SSID_AVAIL: Serial.println("WL_NO_SSID_AVAIL (1) - SSID no disponible"); break;
    case WL_SCAN_COMPLETED: Serial.println("WL_SCAN_COMPLETED (2)"); break;
    case WL_CONNECTED: Serial.println("WL_CONNECTED (3)"); break;
    case WL_CONNECT_FAILED: Serial.println("WL_CONNECT_FAILED (4) - Falló conexión"); break;
    case WL_CONNECTION_LOST: Serial.println("WL_CONNECTION_LOST (5) - Conexión perdida"); break;
    case WL_DISCONNECTED: Serial.println("WL_DISCONNECTED (6) - Desconectado"); break;
    default: Serial.println("Desconocido"); break;
  }

  Serial.print("MAC: ");
  Serial.println(WiFi.macAddress());
  Serial.println("=== FIN DIAGNÓSTICO ===\n");
}
void reconnectMQTT() {
  while (!client.connected() && connectionAttempts < 10) {
    Serial.print("Intentando conexión MQTT...");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Servidor:");
    lcd.setCursor(0, 1);
    lcd.print("Conectando...");
    delay(500);

    // Crear un ID de cliente aleatorio
    String clientId = "DATALOGGER-";
    clientId += String(random(0xffff), HEX);

    // Intentar conectar
    if (client.connect(clientId.c_str())) {
      Serial.println("conectado");
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Servidor:");
      lcd.setCursor(0, 1);
      lcd.print("Conectado");
      delay(500);

      // Suscribirse al tema de comandos
      client.subscribe(mqtt_command_topic);

    } else {
      Serial.print("falló, rc=");
      Serial.print(client.state());
      connectionAttempts++;
      if (connectionAttempts == 10) {
        mqttConnected = false;
        Serial.println("MQTT Error!");
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Servidor:");
        lcd.setCursor(0, 1);
        lcd.print("Error!");
        delay(500);
      } else {
        Serial.println(" intentando de nuevo en 5 segundos");
      }
      delay(5000);
    }
  }
}

String getVoltage() {
  int16_t adc0 = ads.readADC_SingleEnded(0);
  int16_t adc1 = ads.readADC_SingleEnded(1);

  float ch1 = ads.computeVolts(adc0) * 1000.0f;
  float ch2 = ads.computeVolts(adc1) * 1000.0f;

  if (ch1 < 0.0 || ch1 > 11.0) {
    ch1 = 0.0;
  }
  if (ch2 < 0.0 || ch2 > 11.0) {
    ch2 = 0.0;
  }

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Difusa (mv): ");
  lcd.setCursor(12, 0);
  lcd.print(ch1, 2);
  lcd.setCursor(0, 1);
  lcd.print("Global (mV): ");
  lcd.setCursor(12, 1);
  lcd.print(ch2, 2);

  return String(ch1, 2) + "," + String(ch2, 2);
}

String get_data(int id) {
  while (hc.available()) hc.read();  // Limpiar buffer
er
  hc.println(id);  // Enviar solicitud

  unsigned long startTime = millis();
  while (millis() - startTime < 1000) {
    if (hc.available()) {
      String data = hc.readStringUntil('\n');
      data.trim();
      if (data.length() > 0) {
        return data;
      }
    }
  }
  return "Nan,Nan,Nan";
}

bool init_SD() {
  if (!SD.begin(SD_CS_PIN)) {
    Serial.println("Error al inicializar la tarjeta SD");
    return false;
  }

  uint8_t cardType = SD.cardType();
  if (cardType == CARD_NONE) {
    Serial.println("No se detectó tarjeta SD");
    return false;
  }

  // Crear archivo con encabezados si no existe
  if (!SD.exists("/data.csv")) {
    File file = SD.open("/data.csv", FILE_WRITE);
    if (file) {
      file.println("Datetime,Pira_1(mV),Pira_2(mV),Termo1,Termo2,Bat_1,Temp_Amb,Hum_Amb,Bat_2");
      file.close();
    } else {
      Serial.println("Error al crear archivo");
      return false;
    }
  }

  return true;
}

void write_data(String message) {
  DateTime time = rtc.now();

  // Formatear fecha como DD-MM-YYYY HH:MM:SS
  char datetime[20];
  snprintf(datetime, sizeof(datetime), "%02d-%02d-%02d %02d:%02d:%02d",
           time.day(), time.month(), time.year(),       // DD-MM-YYYY
           time.hour(), time.minute(), time.second());  // HH:MM:SS

  String new_message = String(datetime) + "," + message;

  // Abrir archivo en modo append
  dataFile = SD.open("/data.csv", FILE_APPEND);

  if (dataFile) {
    if (dataFile.println(new_message)) {
      Serial.println("Datos guardados: " + new_message);
    } else {
      Serial.println("Error al escribir");
    }
    dataFile.close();
  } else {
    Serial.println("Error al abrir archivo");
    SD_Error = true;
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Mensaje recibido [");
  Serial.print(topic);
  Serial.print("] ");

  // Convertir el payload a String
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.println(message);

  // Verificar si es el tema de comandos y el mensaje es "get"
  if (String(topic) == mqtt_command_topic && message == "get") {
    LeerSensores();
    Serial.println("Comando GET recibido - Leyendo sensores");
  }
}

void LeerSensores() {

  String termopares = get_data(1);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Termopares:");
  lcd.setCursor(0, 1);
  lcd.print(termopares);

  delay(500);
  String ambiente = get_data(2);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Ambiental:");
  lcd.setCursor(0, 1);
  lcd.print(ambiente);

  String message = getVoltage() + "," + termopares + "," + ambiente;

  if (!SD_Error) {
    write_data(message);
  }

  Serial.println("Datos: " + message);

  // Publicar en el tema MQTT solo si estamos conectados
  if (client.connected()) {
    client.publish(mqtt_topic, message.c_str());
  }
}

void setup() {
  Serial.begin(115200);

  lcd.init();
  lcd.backlight();

  hc.begin(9600, SERIAL_8N1, HC12_RX_PIN, HC12_TX_PIN);

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Iniciando sistema...");
  Serial.println("Iniciando sistema...");
  delay(1000);

  lcd.clear();

  // Ejecutar diagnóstico WiFi
  //wifiDiagnostic();

  ads.setGain(GAIN_SIXTEEN);
  //ads.setDataRate(RATE_ADS1115_64SPS);

  if (!ads.begin()) {
    Serial.println("ADC Error!");
    lcd.setCursor(0, 0);
    lcd.print("ADC Error!");
  } else {
    Serial.println("ADC OK!");
    lcd.setCursor(0, 0);
    lcd.print("ADC OK;");
  }

  delay(1000);
  lcd.clear()

    if (!rtc.begin()) {
    Serial.println("RTC Error!");
    lcd.setCursor(0, 0);
    lcd.print("RTC Error!");
    Serial.flush();
    while (1) delay(10);
  }
  lcd.setCursor(0, 1);
  lcd.print("RTC OK!");
  Datetime now = rtc.now();
  lcd.print(now.date());
  lcd.setCursor(0, 1);
  lcd.print(now.hour() + String(":") + now.minutes() + String(":") + now.seconds());
  delay(500);

  if (!rtc.isrunning()) {
    Serial.println("Ajustando RTC...");
    rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
  }

  setup_wifi();

  if (wifiConnected) {
    client.setServer(mqtt_server, mqtt_port);
    client.setCallback(mqttCallback);

    // Dar tiempo para que la conexión WiFi se estabilice
    delay(1000);

    reconnectMQTT();

    if (client.connected()) {
      Serial.println("MQTT conectado exitosamente");
      mqttConnected = true;
    } else {
      Serial.println("MQTT no conectado - continuando en modo offline");
      mqttConnected = false;
      ;
    }
  }

  // Inicializar SD con reintentos
  for (int i = 0; i < 3; i++) {
    if (init_SD()) {
      SD_Error = false;
      break;
    }
    delay(1000);
  }
  lcd.clear();
  if (SD_Error) {
    Serial.println("Sistema iniciado sin tarjeta SD");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Sistema iniciado");
    lcd.setCursor(0, 1);
    lcd.print("SD Error!");
  } else {
    Serial.println("Sistema iniciado correctamente");
    lcd.print("Sistema iniciado");
    lcd.setCursor(0, 1);
    lcd.print("Correctamente");
  }
}

void loop() {
  if (wifiConnected) {
    // Modo online - conexión con el servidor
    if (!client.connected()) {
      reconnectMQTT();
    }
    client.loop();
  }
  if (!wifiConnected || !mqttConnected) {
    // Modo offline - solo guardar en SD
    unsigned long currentMillis = millis();
    if (currentMillis - previousMillis >= interval) {
      previousMillis = currentMillis;
      LeerSensores();
    }
  }
}
