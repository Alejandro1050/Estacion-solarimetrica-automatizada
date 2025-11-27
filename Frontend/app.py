from dash import Dash, html, dcc, Input, Output, callback, dash_table, callback_context
import logging
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import requests
import paho.mqtt.client as mqtt
import threading
import time
from datetime import datetime
from collections import deque
import numpy as np
import subprocess

# Configuración MQTT
MQTT_BROKER_HOST = "localhost"
MQTT_BROKER_PORT = 1883
MQTT_COMMAND_TOPIC = "esp32/commands"
API_URL = "http://localhost:5001/api/get_data"

# URL de la carpeta de Drive
DRIVE_FOLDER_URL = "https://drive.google.com/drive/u/0/folders/1VDvTAz6mSl3Pdbn4T0CL52o68-i0dqpB"

# Buffer para almacenar datos en memoria (últimos 30 minutos)
MAX_DATA_POINTS = 30
data_buffer = {
    'timestamp': deque(maxlen=MAX_DATA_POINTS),
    'DHI': deque(maxlen=MAX_DATA_POINTS),
    'GHI': deque(maxlen=MAX_DATA_POINTS),
    'DNI': deque(maxlen=MAX_DATA_POINTS),
    'temp1': deque(maxlen=MAX_DATA_POINTS),
    'temp2': deque(maxlen=MAX_DATA_POINTS),
    'temp_amb': deque(maxlen=MAX_DATA_POINTS),
    'hum_amb': deque(maxlen=MAX_DATA_POINTS),
    'solar_zenith': deque(maxlen=MAX_DATA_POINTS)
}

# Cliente MQTT global
mqtt_client = None
command_interval = 60  # segundos por defecto
command_thread = None
stop_commands = False

def setup_mqtt():
    """Configura el cliente MQTT"""
    global mqtt_client
    
    def on_connect(client, userdata, flags, rc):
        logging.getLogger(__name__).info("Conectado a MQTT broker con código: %s", rc)
        
    def on_disconnect(client, userdata, rc):
        logging.getLogger(__name__).info("Desconectado del MQTT broker")
    
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    
    try:
        mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
        mqtt_client.loop_start()
        return True
    except Exception as e:
        print(f"Error conectando a MQTT: {e}")
        return False

def send_mqtt_command():
    """Envía comando 'get' por MQTT en intervalos regulares"""
    global stop_commands
    while not stop_commands:
        try:
            if mqtt_client:
                mqtt_client.publish(MQTT_COMMAND_TOPIC, "get")
                print(f"Comando 'get' enviado a {MQTT_COMMAND_TOPIC}")
        except Exception as e:
            print(f"Error enviando comando MQTT: {e}")
        
        time.sleep(command_interval)

def start_command_thread():
    """Inicia el hilo de comandos MQTT"""
    global command_thread, stop_commands
    stop_commands = False
    if command_thread is None or not command_thread.is_alive():
        command_thread = threading.Thread(target=send_mqtt_command, daemon=True)
        command_thread.start()

def stop_command_thread():
    """Detiene el hilo de comandos MQTT"""
    global stop_commands
    stop_commands = True

def fetch_data_from_api():
    """Obtiene datos de la API"""
    try:
        logging.getLogger(__name__).debug("Intentando obtener datos de la API...")
        response = requests.get(API_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            logging.getLogger(__name__).debug("Datos recibidos de API: %s", data)
            if 'data' in data and len(data['data']) > 0:
                last_record = data['data'][-1]
                logging.getLogger(__name__).debug("Último registro: %s", last_record)
                logging.getLogger(__name__).debug("Estados de módulos: temp_status=%s, ambi_status=%s", last_record.get('temp_status'), last_record.get('ambi_status'))
            return data
        else:
            print(f"Error en API: {response.status_code}")
            print(f"Respuesta de error: {response.text}")
        return None
    except Exception as e:
        print(f"Error obteniendo datos de API: {e}")
        return None

def safe_float_convert(value, default=np.nan):
    """Convierte un valor a float de manera segura"""
    if value is None:
        return default
    if isinstance(value, str):
        if value.lower() in ['nan', 'null', '']:
            return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def update_data_buffer(new_data):
    """Actualiza el buffer de datos con nueva información"""
    if not new_data or 'data' not in new_data:
        logging.getLogger(__name__).debug("No hay datos para actualizar")
        return

    logging.getLogger(__name__).debug("Actualizando buffer con %s registros", len(new_data.get('data', [])))
    if new_data.get('data'):
        logging.getLogger(__name__).debug("Primer registro: %s", new_data['data'][0])
        logging.getLogger(__name__).debug("Último registro: %s", new_data['data'][-1])
    logging.getLogger(__name__).debug("Datos recibidos: %s", (new_data['data'][-1] if new_data.get('data') else 'No hay datos'))
    
    for row in new_data.get('data', []):
        try:
            # Convertir timestamp
            timestamp_str = row.get('timestamp', '')
            if timestamp_str:
                # Intentar diferentes formatos de fecha
                try:
                    timestamp = pd.to_datetime(timestamp_str, format='%d-%m-%Y %H:%M:%S')
                except:
                    try:
                        timestamp = pd.to_datetime(timestamp_str, format='%Y-%m-%d %H:%M:%S')
                    except:
                        timestamp = pd.to_datetime(timestamp_str)
            else:
                timestamp = pd.Timestamp.now()

            # Actualizar buffer con manejo seguro de valores
            data_buffer['timestamp'].append(timestamp)
            data_buffer['DHI'].append(safe_float_convert(row.get('DHI(W/m²)', row.get('DHI'))))
            data_buffer['GHI'].append(safe_float_convert(row.get('GHI(W/m²)', row.get('GHI'))))
            data_buffer['DNI'].append(safe_float_convert(row.get('DNI(W/m²)', row.get('DNI'))))
            data_buffer['temp1'].append(safe_float_convert(row.get('temp1', row.get('Temp 1'))))
            data_buffer['temp2'].append(safe_float_convert(row.get('temp2', row.get('Temp 2'))))
            data_buffer['temp_amb'].append(safe_float_convert(row.get('temp_amb', row.get('Temp Amb'))))
            data_buffer['hum_amb'].append(safe_float_convert(row.get('hum_amb', row.get('Hum Amb'))))
        except Exception as e:
            logging.getLogger(__name__).exception("Error procesando fila: %s, fila: %s", e, row)

# Inicializar la aplicación Dash con tema oscuro
app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
app.title = "Estación solarimétrica"

# Layout de la aplicación
app.layout = html.Div([
    # Header
    html.Div([
        html.Button('Apagar sistema', id='power-btn', n_clicks=0, 
                className='btn btn-power', style={'backgroundColor': '#dc3545', 'color': 'white'}),
        html.A(
            html.Button('Carpeta de archivos', id='folder-btn', n_clicks=0,
                      className='btn btn-info'),
            href=DRIVE_FOLDER_URL,
            target='_blank',
            style={'margin-left': '10px'}
        ),
    ], style={'display': 'flex', 'justifyContent': 'flex-end', 'padding': '10px'}),
    
    html.Div([
        html.H1("Estación solarimétrica de la UniCaribe", 
                className="text-center mb-4",
                style={'color': "#4fc3f7", 'margin-bottom': '30px', 'fontWeight': 'bold'})
    ], className="header", style={'backgroundColor': '#303030', 'padding': '20px'}),
    
    # Panel de control - Updated with status indicators
    html.Div([
        html.Div([
            html.H4("Modo de funcionamiento", style={'color': '#e0e0e0', 'marginBottom': '15px'}),
            html.Div([
                # Lado izquierdo: modo y botones
                html.Div([
                    html.Label("Modo:", style={'margin-right': '10px', 'color': '#e0e0e0'}),
                    dcc.Dropdown(
                        id='interval-dropdown',
                        options=[
                            {'label': 'Normal', 'value': 60},
                            {'label': 'Prueba', 'value': 5}
                        ],
                        value=60,  
                        style={'width': '200px', 'display': 'inline-block', 'margin-right': '20px'}
                    ),
                    html.Button('Iniciar monitoreo', id='start-btn', n_clicks=0, 
                               className='btn btn-success', style={'margin-right': '10px'}),
                    html.Button('Detener monitoreo', id='stop-btn', n_clicks=0, 
                               className='btn btn-danger'),
                ], style={'display': 'flex', 'alignItems': 'center', 'flexWrap': 'wrap', 'flex': '1'}),
                
                # Lado derecho: Indicadores de estado de los módulos
                html.Div([
                    html.Div([
                        html.Span("Módulo ambiental: ", style={'color': '#e0e0e0', 'marginRight': '10px'}),
                        html.Span(id="emb-status", children="Activo", 
                                 style={'color': '#4fc3f7', 'fontWeight': 'bold'})
                    ], style={'marginBottom': '10px'}),
                    html.Div([
                        html.Span("Módulo termocuplas: ", style={'color': '#e0e0e0', 'marginRight': '10px'}),
                        html.Span(id="termo-status", children="Activo", 
                                 style={'color': '#4fc3f7', 'fontWeight': 'bold'})
                    ]),
                ], style={'marginLeft': '20px', 'padding': '10px', 'borderLeft': '1px solid #555'})
            ], style={'display': 'flex', 'alignItems': 'center', 'flexWrap': 'wrap'}),
            
            html.Div(id='command-status', style={'margin-top': '10px', 'font-weight': 'bold'}),
            html.Div(id='power-status', style={'margin-top': '10px', 'font-weight': 'bold'}),
            html.Div(id='debug-info', style={'margin-top': '10px', 'font-size': '12px', 'color': '#888'})
        ], className="control-panel", style={'padding': '20px', 'background-color': '#424242', 
                                           'border-radius': '10px', 'margin-bottom': '20px'})
    ]),

    # Resto del layout permanece igual...
    # Indicadores en tiempo real - Radiación
    html.Div([
        html.Div([
            html.H4("☀️ Radiación DHI", style={'color': '#e0e0e0'}),
            html.H2(id="dhi-indicator", children="-- mW/m²", style={'color': '#4fc3f7'})
        ], className="indicator-card", style={'text-align': 'center', 'padding': '20px', 
                                            'background-color': '#424242', 'border-radius': '10px',
                                            'margin': '10px', 'flex': '1', 'border': '1px solid #4fc3f7'}),
        
        html.Div([
            html.H4("☀️ Radiación GHI", style={'color': '#e0e0e0'}),
            html.H2(id="ghi-indicator", children="-- mW/m²", style={'color': '#4fc3f7'})
        ], className="indicator-card", style={'text-align': 'center', 'padding': '20px', 
                                            'background-color': '#424242', 'border-radius': '10px',
                                            'margin': '10px', 'flex': '1', 'border': '1px solid #4fc3f7'}),
        html.Div([
            html.H4("☀️ Radiación DNI", style={'color': '#e0e0e0'}),
            html.H2(id="dni-indicator", children="-- mW/m²", style={'color': '#4fc3f7'})
        ], className="indicator-card", style={'text-align': 'center', 'padding': '20px', 
                                            'background-color': '#424242', 'border-radius': '10px',
                                            'margin': '10px', 'flex': '1', 'border': '1px solid #4fc3f7'})
    ], style={'display': 'flex', 'flex-wrap': 'wrap', 'marginBottom': '20px'}),

    # Indicadores en tiempo real - Temperatura y Humedad
    html.Div([            
        html.Div([
            html.H4("🌡️ Temperatura Superficial", style={'color': '#e0e0e0'}),
            html.H2(id="temp-sup-indicator", children="-- °C", style={'color': '#ff6e6a'})
        ], className="indicator-card", style={'text-align': 'center', 'padding': '20px', 
                                            'background-color': '#424242', 'border-radius': '10px',
                                            'margin': '10px', 'flex': '1', 'border': '1px solid #ff6e6a'}),                                                
        html.Div([
            html.H4("🌡️ Temperatura Ambiente", style={'color': '#e0e0e0'}),
            html.H2(id="temp-amb-indicator", children="-- °C", style={'color': '#ff6e6a'})
        ], className="indicator-card", style={'text-align': 'center', 'padding': '20px', 
                                            'background-color': '#424242', 'border-radius': '10px',
                                            'margin': '10px', 'flex': '1', 'border': '1px solid #ff6e6a'}),
        
        html.Div([
            html.H4("💧 Humedad Ambiente", style={'color': '#e0e0e0'}),
            html.H2(id="hum-amb-indicator", children="-- %", style={'color': '#4fc3f7'})
        ], className="indicator-card", style={'text-align': 'center', 'padding': '20px', 
                                            'background-color': '#424242', 'border-radius': '10px',
                                            'margin': '10px', 'flex': '1', 'border': '1px solid #4fc3f7'})
    ], style={'display': 'flex', 'flex-wrap': 'wrap', 'marginBottom': '20px'}),

    # Gráficas
    html.Div([
        # Gráfica de radiación
        html.Div([
            dcc.Graph(id='radiation-graph')
        ], style={'width': '100%', 'display': 'inline-block'})
    ]),
    
    html.Div([
        # Gráfica de humedad
        html.Div([
            dcc.Graph(id='humidity-graph')
        ], style={'width': '50%', 'display': 'inline-block'}),
        
        # Gráfica de temperatura
        html.Div([
            dcc.Graph(id='temperature-graph')
        ], style={'width': '50%', 'display': 'inline-block'})
    ]),
    
    # Tabla de datos recientes
    html.Div([
        html.H4("Datos Recientes", style={'color': '#e0e0e0', 'margin-top': '30px', 'marginBottom': '15px'}),
        html.Div(id='data-table')
    ], style={'margin-top': '30px'}),
    
    # Interval component para actualizar datos
    dcc.Interval(
        id='interval-component',
        interval=5*1000,  # Actualizar cada 5 segundos
        n_intervals=0
    )
], style={'backgroundColor': '#303030', 'padding': '15px', 'minHeight': '100vh', 'color': '#e0e0e0'})

# Callbacks
@callback(
    [Output('command-status', 'children'),
     Output('command-status', 'style'),
     Output('power-status', 'children'),
     Output('power-status', 'style')],
    [Input('start-btn', 'n_clicks'),
     Input('stop-btn', 'n_clicks'),
     Input('power-btn', 'n_clicks'),
     Input('interval-dropdown', 'value')]
)
def control_mqtt_commands(start_clicks, stop_clicks, power_clicks, interval_value):
    global command_interval
    command_interval = interval_value

    ctx = callback_context
    if not ctx.triggered:
        return "Estado: iniciado automáticamente", {'margin-top': '10px', 'font-weight': 'bold', 'color': '#4fc3f7'}, "", {'display': 'none'}

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == 'start-btn' and start_clicks > 0:
        start_command_thread()
        return (f"Estado: Enviando comandos cada {interval_value}s", 
                {'margin-top': '10px', 'font-weight': 'bold', 'color': '#4fc3f7'},
                "", 
                {'display': 'none'})

    elif button_id == 'stop-btn' and stop_clicks > 0:
        stop_command_thread()
        return ("Estado: Detenido", 
                {'margin-top': '10px', 'font-weight': 'bold', 'color': '#ff6e6a'},
                "", 
                {'display': 'none'})

    elif button_id == 'power-btn' and power_clicks > 0:
        # Detener comandos MQTT primero
        stop_command_thread()
        
        # Mostrar mensaje de apagado
        power_message = "⚠️ SISTEMA APAGÁNDOSE - El servidor se apagará en 10 segundos"
        power_style = {'margin-top': '10px', 'font-weight': 'bold', 'color': '#ff6e6a', 'fontSize': '16px', 'backgroundColor': '#300000', 'padding': '10px', 'borderRadius': '5px'}
        
        # Función para apagar el sistema en segundo plano
        def shutdown_system():
            time.sleep(10)  # Dar 10 segundos para que el usuario vea el mensaje
            
            try:
                logger = logging.getLogger(__name__)
                logger.info("Apagando el sistema completo desde la interfaz web")
                
                subprocess.run(['sudo', 'poweroff'], check=False)
                
            except Exception as e:
                logger.error(f"Error al apagar el sistema: {e}")
        
        # Ejecutar el apagado en un hilo separado
        shutdown_thread = threading.Thread(target=shutdown_system, daemon=True)
        shutdown_thread.start()
        
        return ("Estado: APAGANDO SISTEMA...", 
                {'margin-top': '10px', 'font-weight': 'bold', 'color': '#ff6e6a', 'fontSize': '14px'},
                power_message, 
                power_style)

    return ("Estado: Detenido", 
            {'margin-top': '10px', 'font-weight': 'bold', 'color': '#ff6e6a'},
            "", 
            {'display': 'none'})

@app.callback(
    [Output('radiation-graph', 'figure'),
     Output('temperature-graph', 'figure'),
     Output('humidity-graph', 'figure'),
     Output('temp-amb-indicator', 'children'),
     Output('hum-amb-indicator', 'children'),
     Output('dhi-indicator', 'children'),
     Output('ghi-indicator', 'children'),
     Output('dni-indicator', 'children'),
     Output('temp-sup-indicator', 'children'),
     Output('data-table', 'children'),
     Output('debug-info', 'children'),
     Output('emb-status', 'children'),
     Output('emb-status', 'style'),
     Output('termo-status', 'children'),
     Output('termo-status', 'style')],
    [Input('interval-component', 'n_intervals')]
)
def update_dashboard(n):
    # Obtener nuevos datos de la API
    new_data = fetch_data_from_api()
    update_data_buffer(new_data)

    # Obtener estados por defecto
    temp_module_status = 'Activo'
    amb_module_status = 'Activo'

    # Extraer estados si la API los entrega en el último registro
    try:
        if new_data and 'data' in new_data and len(new_data['data']) > 0:
            last = new_data['data'][-1]
            if 'temp_status' in last and last['temp_status'] is not None:
                temp_module_status = last['temp_status']
            if 'ambi_status' in last and last['ambi_status'] is not None:
                amb_module_status = last['ambi_status']
    except Exception as e:
        print(f"Error extrayendo estados de módulos: {e}")

    debug_info = f"Última actualización: {datetime.now().strftime('%H:%M:%S')} - Buffer size: {len(data_buffer['timestamp'])}"
    
    # Actualizar indicadores de estado
    emb_style = {'color': '#4fc3f7', 'fontWeight': 'bold'} if amb_module_status == 'Activo' else {'color': '#ff6e6a', 'fontWeight': 'bold'}
    termo_style = {'color': '#4fc3f7', 'fontWeight': 'bold'} if temp_module_status == 'Activo' else {'color': '#ff6e6a', 'fontWeight': 'bold'}

    if len(data_buffer['timestamp']) == 0:
        # Crear gráficas vacías si no hay datos
        empty_fig = go.Figure()
        empty_fig.update_layout(
            title="Sin datos disponibles",
            plot_bgcolor='#303030',
            paper_bgcolor='#424242',
            font={'color': '#e0e0e0'}
        )
        return (
            empty_fig,
            empty_fig,
            empty_fig,
            "-- °C",
            "-- %",
            "-- W/m²",
            "-- W/m²",
            "-- W/m²",
            "-- °C",
            html.Div("Sin datos disponibles", style={'color': '#ff6e6a'}),
            debug_info,
            amb_module_status,
            emb_style,
            temp_module_status,
            termo_style
        )

    # Convertir buffer a DataFrame
    df = pd.DataFrame({
        'timestamp': list(data_buffer['timestamp']),
        'DHI': list(data_buffer['DHI']),
        'GHI': list(data_buffer['GHI']),
        'DNI': list(data_buffer['DNI']),
        'temp1': list(data_buffer['temp1']),
        'temp2': list(data_buffer['temp2']),
        'temp_amb': list(data_buffer['temp_amb']),
        'hum_amb': list(data_buffer['hum_amb'])
    })

    # Gráfica de radiación
    radiation_fig = go.Figure()
    if not df['DHI'].isna().all():
        radiation_fig.add_trace(go.Scatter(
            x=df['timestamp'], y=df['DHI'],
            mode='lines+markers', name='DHI',
            line=dict(color='#e74c3c', width=2)
        ))
    if not df['GHI'].isna().all():
        radiation_fig.add_trace(go.Scatter(
            x=df['timestamp'], y=df['GHI'],
            mode='lines+markers', name='GHI',
            line=dict(color='#f39c12', width=2)
        ))
    if not df['DNI'].isna().all():
        radiation_fig.add_trace(go.Scatter(
            x=df['timestamp'], y=df['DNI'],
            mode='lines+markers', name='DNI',
            line=dict(color="#4fc3f7", width=2)
        ))
    radiation_fig.update_layout(
        title='Radiación Solar en Tiempo Real',
        xaxis_title='Tiempo',
        yaxis_title='Radiación (mW/m²)',
        hovermode='x unified',
        template='plotly_dark',
        plot_bgcolor='#424242',
        paper_bgcolor='#424242',
        font={'color': '#e0e0e0'}
    )
    
    # Gráfica de temperatura
    temp_fig = go.Figure()
    if not df['temp1'].isna().all():
        temp_fig.add_trace(go.Scatter(
            x=df['timestamp'], y=df['temp1'],
            mode='lines+markers', name='Temperatura 1',
            line=dict(color='#ff6e6a', width=2),
            fill='none'
        ))
        
    if not df['temp2'].isna().all():
        temp_fig.add_trace(go.Scatter(
            x=df['timestamp'], y=df['temp2'],
            mode='lines+markers', name='Temperatura 2',
            line=dict(color='#9b59b6', width=2)
        ))
    if not df['temp_amb'].isna().all():
        temp_fig.add_trace(go.Scatter(
            x=df['timestamp'], y=df['temp_amb'],
            mode='lines+markers', name='Temp. Ambiente',
            line=dict(color='#4fc3f7', width=2)
        ))
    temp_fig.update_layout(
        title='Temperaturas en Tiempo Real',
        xaxis_title='Tiempo',
        yaxis_title='Temperatura (°C)',
        hovermode='x unified',
        template='plotly_dark',
        plot_bgcolor='#424242',
        paper_bgcolor='#424242',
        font={'color': '#e0e0e0'}
    )
    
    # Gráfica de humedad
    humidity_fig = go.Figure()
    if not df['hum_amb'].isna().all():
        humidity_fig.add_trace(go.Scatter(
            x=df['timestamp'], y=df['hum_amb'],
            mode='lines+markers', name='Humedad Ambiente',
            line=dict(color='#17a2b8', width=2),
            fill='none'
        ))
    humidity_fig.update_layout(
        title='Humedad Ambiente en Tiempo Real',
        xaxis_title='Tiempo',
        yaxis_title='Humedad (%)',
        hovermode='x unified',
        template='plotly_dark',
        plot_bgcolor='#424242',
        paper_bgcolor='#424242',
        font={'color': '#e0e0e0'}
    )
    
    # Indicadores
    def format_value(value, unit, decimals=1):
        if pd.isna(value) or value is None:
            return f"-- {unit}"
        return f"{value:.{decimals}f} {unit}"
    
    last_temp_amb = format_value(df['temp_amb'].iloc[-1] if len(df) > 0 else np.nan, "°C")
    last_hum_amb = format_value(df['hum_amb'].iloc[-1] if len(df) > 0 else np.nan, "%")
    last_dhi = format_value(df['DHI'].iloc[-1] if len(df) > 0 else np.nan, "W/m²")
    last_ghi = format_value(df['GHI'].iloc[-1] if len(df) > 0 else np.nan, "W/m²")
    last_dni = format_value(df['DNI'].iloc[-1] if len(df) > 0 else np.nan, "W/m²")
    
    # Calcular temperatura superficial promedio
    if len(df) > 0:
        temp1_val = df['temp1'].iloc[-1]
        temp2_val = df['temp2'].iloc[-1]
        if pd.notna(temp1_val) and pd.notna(temp2_val):
            temp_sup = (temp1_val + temp2_val) / 2
        elif pd.notna(temp1_val):
            temp_sup = temp1_val
        elif pd.notna(temp2_val):
            temp_sup = temp2_val
        else:
            temp_sup = np.nan
    else:
        temp_sup = np.nan
    
    last_temp_sup = format_value(temp_sup, "°C")

    # Tabla de datos recientes (últimos 10 registros)
    if len(df) > 0:
        recent_df = df.tail(10).copy()
        recent_df['timestamp'] = recent_df['timestamp'].dt.strftime('%H:%M:%S')
        
        # Renombrar columnas para la tabla
        recent_df_display = recent_df.rename(columns={
            'timestamp': 'Hora',
            'DHI': 'DHI (W/m²)',
            'GHI': 'GHI (W/m²)',
            'DNI': 'DNI (W/m²)',
            'temp1': 'Temp 1 (°C)',
            'temp2': 'Temp 2 (°C)',
            'temp_amb': 'Temp Amb (°C)',
            'hum_amb': 'Hum Amb (%)'
        })
        
        # Redondear valores numéricos
        for col in recent_df_display.columns:
            if col != 'Hora':
                recent_df_display[col] = recent_df_display[col].round(1)

        table = dash_table.DataTable(
            data=recent_df_display.to_dict('records'),
            columns=[{"name": i, "id": i} for i in recent_df_display.columns],
            style_cell={
                'textAlign': 'center', 
                'fontSize': '12px',
                'backgroundColor': '#424242',
                'color': '#e0e0e0',
                'border': '1px solid #303030'
            },
            style_header={
                'backgroundColor': '#303030',
                'fontWeight': 'bold',
                'color': '#e0e0e0',
                'border': '1px solid #303030'
            },
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': '#4a4a4a'
                }
            ],
            style_table={'overflowX': 'auto'}
        )
    else:
        table = html.Div("Sin datos para mostrar", style={'color': '#888'})

    return (radiation_fig, temp_fig, humidity_fig,
            last_temp_amb, last_hum_amb, last_dhi, last_ghi, last_dni, last_temp_sup, table, debug_info,
            amb_module_status, emb_style, temp_module_status, termo_style)

if __name__ == '__main__':
    # Configurar MQTT al iniciar
    print("Configurando conexión MQTT...")
    if setup_mqtt():
        print("MQTT configurado correctamente")

        # iniciar monitoreo automáticamente en modo normal
        command_interval = 60  # Normal mode
        start_command_thread()
        print("Monitoreo iniciado automáticamente en modo Normal")
    else:
        print("Error configurando MQTT - continuando sin conexión MQTT")
    
    print("Iniciando dashboard...")
    app.run(debug=True, host='0.0.0.0', port=8050)