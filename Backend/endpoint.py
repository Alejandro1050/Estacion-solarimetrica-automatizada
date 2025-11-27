from flask import Flask, jsonify, request
import polars as ps
import os
from datetime import datetime
import numpy as np
import math
import logging

app = Flask(__name__)

# Logger
logger = logging.getLogger(__name__)

# Configure centralized logging
from logging_config import configurar_logging
configurar_logging()

# Variables globales para almacenar datos en memoria
recent_data = []
MAX_MEMORY_RECORDS = 30

def clean_value(value):
    """Limpia y convierte valores, maneja NaN correctamente"""
    if value is None:
        return None
    
    # Si es string
    if isinstance(value, str):
        if value.lower() in ['nan', 'null', '']:
            return None
        try:
            return float(value)
        except ValueError:
            return None
    
    # Si es float
    if isinstance(value, float):
        if math.isnan(value):
            return None
        return value
    
    # Si es int
    if isinstance(value, int):
        return float(value)
    
    return None

@app.route('/api/push_data', methods=['POST'])
def push_data():
    """Endpoint que recibe datos del MQTT handler"""
    global recent_data
    try:
        data = request.get_json()
        logger.debug("Datos recibidos en push_data: %s", data)

        raw_row = data.get('raw_row', {})
        etl_row = data.get('etl_row', {})

        # Priorizar etl_row si existe, sino usar raw_row
        source_row = etl_row if etl_row else raw_row

        # Agregar timestamp si no existe
        timestamp = source_row.get('timestamp', source_row.get('Timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        # Debug para los estados
        logger.debug("Estados recibidos - temp_status: %s, ambi_status: %s", source_row.get('temp_status'), source_row.get('ambi_status'))

        # Formatear datos para el dashboard
        formatted_data = {
            'timestamp': timestamp,
            'DHI(W/m²)': clean_value(source_row.get('DHI(W/m²)', source_row.get('DHI', source_row.get('ch1_etl')))),
            'GHI(W/m²)': clean_value(source_row.get('GHI(W/m²)', source_row.get('GHI', source_row.get('ch2_etl')))),
            'DNI(W/m²)': clean_value(source_row.get('DNI(W/m²)', source_row.get('DNI', source_row.get('ch3_etl')))),
            'temp1': clean_value(source_row.get('temp1', source_row.get('Temp 1'))),
            'temp2': clean_value(source_row.get('temp2', source_row.get('Temp 2'))),
            'temp_amb': clean_value(source_row.get('temp_amb', source_row.get('Temp Amb'))),
            'hum_amb': clean_value(source_row.get('hum_amb', source_row.get('Hum Amb'))),
            'temp_status': source_row.get('temp_status', None),
            'ambi_status': source_row.get('ambi_status', None),
            'solar_zenith': clean_value(source_row.get('solar_zenith', source_row.get('Solar Zenith')))
        }

        logger.debug("Datos formateados: %s", formatted_data)

        # Mantener solo los últimos registros en memoria
        recent_data.append(formatted_data)
        if len(recent_data) > MAX_MEMORY_RECORDS:
            recent_data = recent_data[-MAX_MEMORY_RECORDS:]

        return jsonify({"status": "success"}), 200

    except Exception as e:
        logger.exception("Error en push_data: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/get_data', methods=['GET'])
def get_data():
    """Endpoint para que el dashboard obtenga los datos"""
    global recent_data

    try:
        # Obtener parámetros de consulta opcionales
        limit = request.args.get('limit', 100, type=int)

        # Devolver los datos más recientes
        data_to_return = recent_data[-limit:] if len(recent_data) > limit else recent_data

        return jsonify({
            "status": "success",
            "count": len(data_to_return),
            "data": data_to_return,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.exception("Error en get_data: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/get_historical_data', methods=['GET'])
def get_historical_data():
    """Endpoint para obtener datos históricos desde archivos CSV"""
    try:
        date_param = request.args.get('date', datetime.now().strftime("%d-%m-%Y"))
        data_type = request.args.get('type', 'etl')  # 'raw' o 'etl'

        if data_type == 'raw':
            file_path = f"/home/barba_negra/data/{date_param}_raw_data.csv"
        else:
            file_path = f"/home/barba_negra/data/{date_param}_etl_data.csv"

        if not os.path.exists(file_path):
            return jsonify({"error": "Archivo no encontrado", "file": file_path}), 404

        # Leer CSV con polars
        df = ps.read_csv(file_path)

        # Convertir a diccionario
        data = df.to_dicts()

        return jsonify({
            "status": "success",
            "count": len(data),
            "data": data,
            "file": file_path,
            "type": data_type
        }), 200

    except Exception as e:
        logger.exception("Error en get_historical_data: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Endpoint para verificar que la API está funcionando"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "recent_data_count": len(recent_data)
    }), 200

if __name__ == '__main__':
    # Configure basic logging for standalone run
    logging.basicConfig(level=logging.INFO)
    app.run(host='0.0.0.0', port=5001, debug=True)