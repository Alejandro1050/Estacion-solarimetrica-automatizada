import paho.mqtt.client as mqtt
import random
import time
from datetime import datetime
import math

# Configuración del simulador
MQTT_BROKER_HOST = "localhost"
MQTT_BROKER_PORT = 1883
MQTT_TOPIC = "esp32/sensors"
MQTT_COMMAND_TOPIC = "esp32/commands"

# Rangos de valores realistas para cada sensor
RANGES = {
    'ch1': (0, 10),
    'ch2': (0, 10),
    'temp_1': (20, 80),
    'temp_2': (20, 80),
    'bat_2': (3.0, 4.2),
    'temp_amb': (15, 35),
    'hum_amb': (30, 80),
    'bat_3': (3.0, 4.2)
}

client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    print(f"Conectado al broker MQTT con código: {rc}")
    client.subscribe(MQTT_COMMAND_TOPIC)
    print(f"Suscrito a {MQTT_COMMAND_TOPIC}")

def generate_sensor_data():
    """Genera datos aleatorios dentro de rangos realistas"""
    data = {
        'ch1': round(random.uniform(*RANGES['ch1']),2),
        'ch2': round(random.uniform(*RANGES['ch2']),2),
        'temp_1': round(random.uniform(*RANGES['temp_1']),2),
        'temp_2': round(random.uniform(*RANGES['temp_2']),2),
        'bat_2': round(random.uniform(*RANGES['bat_2']),2),
        'temp_amb': round(random.uniform(*RANGES['temp_amb']),2),
        'hum_amb': round(random.uniform(*RANGES['hum_amb']),2),
        'bat_3': round(random.uniform(*RANGES['bat_3']),2)
    }
    # Ocasionalmente generar valores NaN (1% de probabilidad)
    for key in data:
        if random.random() < 0.01:
            data[key] = float('nan')
    return data

def on_message(client, userdata, msg):
    if msg.topic == MQTT_COMMAND_TOPIC:
        payload = msg.payload.decode('utf-8').strip().lower()
        if payload == "get":
            data = generate_sensor_data()
            # Reemplaza nan por 0 o por "" si lo deseas
            for k, v in data.items():
                if isinstance(v, float) and math.isnan(v):
                    data[k] = ""
            payload_str = f"{data['ch1']},{data['ch2']},{data['temp_1']}," \
                          f"{data['temp_2']},{data['bat_2']},{data['temp_amb']}," \
                          f"{data['hum_amb']},{data['bat_3']}"
            client.publish(MQTT_TOPIC, payload_str)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Datos publicados: {payload_str}")

if __name__ == "__main__":
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("Deteniendo simulador...")
    finally:
        client.loop_stop()
        client.disconnect()