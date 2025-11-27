import paho.mqtt.client as mqtt
import csv
import os
from datetime import datetime
import time
import email_alert
from pathlib import Path
import polars as ps
import math 
import threading
import requests
import logging
import pytz
import pvlib
from pvlib import solarposition
import pandas as pd

# Configuración del broker MQTT
MQTT_BROKER_HOST = "localhost"  
MQTT_BROKER_PORT = 1883
MQTT_TOPIC = "esp32/sensors"

# Configuración geográfica 
LATITUD = 21.947  
LONGITUD = -86.4948
ALTITUD = 10  # Altitud en metros 
TIMEZONE = 'America/Cancun'

# Archivo CSV para almacenar los datos
date = datetime.now().strftime("%d-%m-%Y") # dd-mm-aaaa
RAW_FILE = (f"/home/barba_negra/data/{date}_raw_data.csv")
ETL_FILE = (f"/home/barba_negra/data/{date}_etl_data.csv")

# Variables para almacenar datos
timestamps = []
ch1_arr = []
ch2_arr = []
temp_1_arr = []
temp_2_arr = []
bat_1_arr = []
temp_amb_arr = []
hum_amb_arr = []
bat_2_arr = []
const_pira_1 = 8.66 #uV/(W/m²) Constante para el piranómetro #1 de la radiación difusa en microvolts
const_pira_2 = 8.72 #uV/(W/m²) Constante para el piranómetro #2 de la radiación global en microvolts

temp_status = "Activo"
ambi_status = "Activo"

# Objetos para enviar correos electrónicos
termopar_error = "Termopares error"  
ambiental_error = "Ambiental error"

error_count_termo = 0
error_count_ambi = 0

# Logger
logger = logging.getLogger(__name__)

def calcular_posicion_solar(timestamp_str):
    """
    Calcula la posición solar (usando pvlib) para un timestamp dado
    """
    try:
        # Convertir string a datetime object con timezone
        dt_local = datetime.strptime(timestamp_str, "%d-%m-%Y %H:%M:%S")
        local_tz = pytz.timezone(TIMEZONE)
        dt_local = local_tz.localize(dt_local)
        
        # Convertir a UTC para pvlib
        dt_utc = dt_local.astimezone(pytz.UTC)
        
        # Crear DataFrame con el timestamp
        times = pd.DatetimeIndex([dt_utc])
        
        # Calcular posición solar
        solar_pos = solarposition.get_solarposition(
            times, 
            LATITUD, 
            LONGITUD, 
            ALTITUD
        )
        
        return {
            'zenith': solar_pos['zenith'].iloc[0],  # Ángulo cenital en grados
            'apparent_zenith': solar_pos['apparent_zenith'].iloc[0],
            'elevation': solar_pos['elevation'].iloc[0],  # Elevación solar en grados
            'azimuth': solar_pos['azimuth'].iloc[0]  # Acimut solar en grados
        }
        
    except Exception as e:
        logger.exception("Error calculando posición solar: %s", e)
        # Valores por defecto (mediodía solar)
        return {
            'zenith': 45.0,
            'apparent_zenith': 45.0,
            'elevation': 45.0,
            'azimuth': 180.0
        }

def calcular_dni(ghi, dhi, timestamp_str):
    """
    Calcula el DNI (Direct Normal Irradiance) estimado.
    """
    # Validación de valores nulos/inválidos
    try:
        ghi_val = float(ghi)
        dhi_val = float(dhi)
    except (ValueError, TypeError):
        return None
    
    # Valores negativos o NaN
    if math.isnan(ghi_val) or math.isnan(dhi_val) or ghi_val < 0 or dhi_val < 0:
        return None
    
    try:
        solar_pos = calcular_posicion_solar(timestamp_str)
        zenith = solar_pos['apparent_zenith']

        # Sol debajo del horizonte → DNI = 0
        if zenith >= 87: 
            return 0.0

        zenith_rad = math.radians(zenith)
        cos_zenith = math.cos(zenith_rad)

        # Validar que cos_zenith sea positivo y significativo
        if cos_zenith <= 0.01:  # ~89.4 grados
            return 0.0

        # Cálculo del DNI
        dni_estimado = (ghi_val - dhi_val) / cos_zenith
        
        # Si DNI es negativo, algo está mal (DHI > GHI)
        if dni_estimado < 0:
            return 0.0

        # Coeficiente de claridad
        extraterrestrial_irradiance = 1361 * cos_zenith
        kt = ghi_val / extraterrestrial_irradiance if extraterrestrial_irradiance > 0 else 0

        # Corrección empírica basada en coeficiente de claridad
        if kt > 0.8:  # Cielo muy despejado
            dni_corregido = dni_estimado * 1.05
        elif kt > 0.6:  # Cielo parcialmente despejado
            dni_corregido = dni_estimado * 1.02
        elif kt > 0.3:  # Cielo nublado
            dni_corregido = dni_estimado * 0.98
        else:  # Cielo muy nublado
            dni_corregido = dni_estimado * 0.95

        dni_final = min(max(0.0, dni_corregido), 1500.0)
        
        # Debug log para valores anormales
        if dni_final > 1200:
            logger.warning(f"DNI alto detectado: {dni_final:.1f} W/m² | GHI={ghi_val:.1f} | DHI={dhi_val:.1f} | Zenith={zenith:.1f}°")
            
        return round(dni_final, 2)

    except Exception as e:
        logger.error(f"Error calculando DNI para {timestamp_str}: {e}")
        return None

def calcular_componentes_radiacion(ghi, dhi, timestamp_str):
    """
    Calcula todos los componentes de la radiación solar
    """
    dni = calcular_dni(ghi, dhi, timestamp_str)
    
    # Calcular DHI (ya la tenemos) y validar
    dhi_final = float(dhi) if dhi != 'nan' else 0.0
    dhi_final = max(0.0, dhi_final)
    
    # Calcular GHI (ya la tenemos) y validar
    ghi_final = float(ghi) if ghi != 'nan' else 0.0
    ghi_final = max(0.0, ghi_final)
    
    return {
        'DHI': dhi_final,
        'GHI': ghi_final,
        'DNI': dni if dni != 'nan' else 0.0
    }

def radiacion_total(columna, valor):
    try:
        if not os.path.exists(ETL_FILE):
            return valor
        
        df = ps.read_csv(ETL_FILE, truncate_ragged_lines=True)
        
        if len(df) > 0 and columna in df.columns:
            last_value = df[columna][-1]
            if not (isinstance(last_value, str) and last_value.lower() == 'nan'):
                salida = float(last_value) + float(valor)
            else:
                salida = float(valor)
        else: 
            salida = float(valor)
    except Exception as e:
        logger.exception("Error en radiacion_total: %s", e)
        salida = float(valor)
    
    return salida

def is_nan_value(value):
    if isinstance(value, str):
        return value.lower() in ['nan', 'null', '']
    elif isinstance(value, float):
        return math.isnan(value)
    return False

def safe_float_or_nan(value):
    """Convierte un valor a float, o devuelve 'nan' como string si no es válido"""
    try:
        if isinstance(value, str) and value.lower() in ['nan', 'null', '']:
            return 'nan'
        return float(value)
    except (ValueError, TypeError):
        return 'nan'

# Crear el archivo CSV si no existe
if not os.path.exists(RAW_FILE):
    with open(RAW_FILE, 'w', newline='') as file_raw:
        writer_raw = csv.writer(file_raw)
        writer_raw.writerow(["Timestamp", "Pira 1(mV)", "Pira 2(mV)", "Temp 1", "Temp 2", "Bat 1", "Temp Amb", "Hum Amb", "Bat 2"])

if not os.path.exists(ETL_FILE):
    with open(ETL_FILE, 'w', newline='') as file_etl:
        writer_etl = csv.writer(file_etl)
        writer_etl.writerow(["Timestamp", "DHI(W/m²)", "GHI(W/m²)", "DNI(W/m²)", "Temp 1", "Temp 2", "Temp Amb", "Hum Amb", "GHI(W/m²) acumulada", "DHI(W/m²) acumulada", "DNI(W/m²) acumulada"])

# Callback cuando se conecta al broker
def on_connect(client, userdata, flags, rc):
    logger.info("Conectado al broker MQTT con código: %s", rc)
    client.subscribe(MQTT_TOPIC)
    logger.info("Suscrito al tema: %s", MQTT_TOPIC)
    logger.info("Esperando solicitudes...")

# Callback cuando se recibe un mensaje
def on_message(client, userdata, msg):
    global error_count_termo, error_count_ambi, temp_status, ambi_status

    try:
        # Decodificar el mensaje recibido 
        payload = msg.payload.decode('utf-8')
        ch1, ch2, temp_1, temp_2, bat_1, temp_amb, hum_amb, bat_2 = map(float, payload.split(','))
        
        # Obtener timestamp actual
        timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        
        # Guardar en el CSV raw
        with open(RAW_FILE, 'a', newline='') as file_raw:
            writer_raw = csv.writer(file_raw)
            writer_raw.writerow([timestamp, ch1, ch2, temp_1, temp_2, bat_1, temp_amb, hum_amb, bat_2])

        # Verificación de errores
        if is_nan_value(temp_1) or is_nan_value(temp_2):   
            logger.debug("Error Temp Count: %s", error_count_termo)
            error_count_termo += 1
            if error_count_termo == 5:
                threading.Thread(target=email_alert.error_alert, args=("Termopares", termopar_error)).start()
                temp_status = "Error"
                error_count_termo = 0
        else: 
            error_count_termo = 0
            temp_status = "Activo"

        if is_nan_value(temp_amb) or is_nan_value(hum_amb):   
            logger.debug("Error Ambi Count: %s", error_count_ambi)
            error_count_ambi += 1
            if error_count_ambi == 5:
                threading.Thread(target=email_alert.error_alert, args=("Ambiental", ambiental_error)).start()
                ambi_status = "Error"
                error_count_ambi = 0
        else: 
            error_count_ambi = 0
            ambi_status = "Activo"

        # Procesar datos ETL
        if not is_nan_value(ch1):
            ch1_etl, pira_1_total = etl(ch1, const_pira_1, "Pira 1 Total")
        else:
            ch1_etl, pira_1_total = 'nan', 0

        if not is_nan_value(ch2):
            ch2_etl, pira_2_total = etl(ch2, const_pira_2, "Pira 2 Total")
        else:
            ch2_etl, pira_2_total = 'nan', 0

        # CALCULAR DNI 
        if ch1_etl != 'nan' and ch2_etl != 'nan':
            componentes = calcular_componentes_radiacion(ch2_etl, ch1_etl, timestamp)
            ch1_final = componentes['DHI']
            ch2_final = componentes['GHI']
            ch3_final = componentes['DNI']
        else:
            ch1_final = ch1_etl
            ch2_final = ch2_etl
            ch3_final = 'nan'
   
        # Guardar los datos procesados en el archivo ETL
        with open(ETL_FILE, 'a', newline='') as file_etl:
            writer_etl = csv.writer(file_etl)
            writer_etl.writerow([timestamp, ch1_final, ch2_final, ch3_final, temp_1, temp_2, temp_amb, hum_amb, pira_1_total, pira_2_total])               
            
        logger.debug("Datos recibidos - Pira 1: %s, Pira 2: %s, Temp 1: %s, Temp 2: %s, Bat 1: %s, Temp Amb: %s, Hum Amb: %s, Bat 2: %s", ch1, ch2, temp_1, temp_2, bat_1, temp_amb, hum_amb, bat_2)

        # Preparar datos para enviar a la API
        raw_row = {
            'Timestamp': timestamp,
            'Pira 1(mV)': ch1,
            'Pira 2(mV)': ch2,
            'Temp 1': temp_1,
            'Temp 2': temp_2,
            'Bat 1': bat_1,
            'Temp Amb': temp_amb,
            'Hum Amb': hum_amb,
            'Bat 2': bat_2
        }

        etl_row = {
            'timestamp': timestamp,
            'DHI(W/m²)': ch1_final if ch1_final != 'nan' else None,
            'GHI(W/m²)': ch2_final if ch2_final != 'nan' else None,
            'DNI(W/m²)': ch3_final if ch3_final != 'nan' else None,
            'temp1': temp_1,
            'temp2': temp_2,
            'temp_amb': temp_amb,
            'hum_amb': hum_amb,
            'temp_status': temp_status,
            'ambi_status': ambi_status,
            'solar_zenith': calcular_posicion_solar(timestamp)['zenith']  
        }

        # Enviar datos a la API
        try:
            api_url = "http://localhost:5001/api/push_data"
            payload = {
                "raw_row": raw_row,
                "etl_row": etl_row
            }
            
            logger.debug("Enviando a API: %s", payload)
            response = requests.post(api_url, json=payload, timeout=5)
            logger.debug("Respuesta API: %s", response.status_code)
            
        except Exception as e:
            logger.exception("Error enviando datos a la API: %s", e)

    except Exception as e:
        logger.exception("Error al procesar el mensaje: %s", e)

def etl_process(channel, constante):
    
    # Convierte señal del piranómetro (mV) a radiación (W/m²)
    try:
        # Convertir mV a µV y dividir entre la constante
        channel_processed = (float(channel) * 1000) / constante
        return channel_processed
    except Exception as e:
        logger.exception("Error en etl_process: %s", e)
        return 'nan'

def etl(channel, constante, columna, etl_file=ETL_FILE):

    try:
        valor_procesado = (float(channel) * 1000) / constante
    except Exception:
        valor_procesado = 'nan'
    try:
        if not os.path.exists(etl_file):
            return valor_procesado, float(valor_procesado) if valor_procesado != 'nan' else 0.0

        df = ps.read_csv(etl_file, truncate_ragged_lines=True)
        if len(df) > 0 and columna in df.columns:
            last_value = df[columna][-1]
            if not (isinstance(last_value, str) and last_value.lower() == 'nan'):
                total = float(last_value) + (float(valor_procesado) if valor_procesado != 'nan' else 0.0)
            else:
                total = float(valor_procesado) if valor_procesado != 'nan' else 0.0
        else:
            total = float(valor_procesado) if valor_procesado != 'nan' else 0.0
    except Exception as e:
        logger.exception("Error en ETL: %s", e)
        total = float(valor_procesado) if valor_procesado != 'nan' else 0.0

    return valor_procesado, total

def clean_nans(d):
    """Convierte todos los float nan en None para que el JSON sea válido."""
    result = {}
    for k, v in d.items():
        if isinstance(v, float) and math.isnan(v):
            result[k] = None
        elif isinstance(v, str) and v.lower() == 'nan':
            result[k] = None
        else:
            result[k] = v
    return result

# Configurar el cliente MQTT
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# Conectar al broker
try:
    client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
except Exception as e:
    logger.exception("Error al conectar al broker MQTT: %s", e)
    logger.error("Asegúrate de tener un broker MQTT ejecutándose en la dirección especificada.")
    raise

# Iniciar el cliente en un hilo separado
client.loop_start()

# Mensaje informativo usando logging
logger.info("Sistema de monitoreo iniciado. Presiona Ctrl+C para detener.")
logger.info(f"Ubicación configurada: Lat {LATITUD}, Lon {LONGITUD}, Alt {ALTITUD}m")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Cerrando la aplicación...")
finally:
    client.loop_stop()
    client.disconnect()
    logger.info("Cliente MQTT desconectado.")