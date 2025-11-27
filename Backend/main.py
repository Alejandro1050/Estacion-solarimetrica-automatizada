import datetime
import subprocess
import time
import email_alert 
import logging
from logging_config import configurar_logging

# Configura un logging centralizado (crea logs/ y archivo rotativo)
configurar_logging()

def start_script(script_name):
    # Inicia el script indicado y retorna el proceso
    proc = subprocess.Popen(['python3', script_name])
    logging.getLogger(__name__).info("Started %s with PID %s", script_name, proc.pid)
    return proc

def stop_script(proc):
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()

etl_proc = None
endpoint_proc = None
frontend_proc = None
load_proc = None
graph_proc = None

# Logger
logger = logging.getLogger(__name__)

def ensure_services():
    """Asegura que todos los servicios necesarios estén corriendo"""
    global etl_proc, endpoint_proc, frontend_proc
    
    # Iniciar endpoint si no está corriendo
    if not endpoint_proc or endpoint_proc.poll() is not None:
        endpoint_proc = start_script('/home/barba_negra/SolarServer/backend/endpoint.py')
        logger.info("Endpoint iniciado")
    
    # Iniciar ETL si no está corriendo
    if not etl_proc or etl_proc.poll() is not None:
        etl_proc = start_script('/home/barba_negra/SolarServer/backend/etl.py')
        logger.info("ETL iniciado")
    
    # Iniciar frontend si no está corriendo (opcional)
    if not frontend_proc or frontend_proc.poll() is not None:
        frontend_proc = start_script('/home/barba_negra/SolarServer/frontend/app.py')
        logger.info("Frontend iniciado")

while True:
    now = datetime.datetime.now()
    hour = now.hour
    minute = now.minute

    # 23:59 - Detener ETL y arrancar LOAD
    if hour == 23 and minute == 59:
        if etl_proc:
            stop_script(etl_proc)
            etl_proc = None
        if not load_proc or load_proc.poll() is not None:
            load_proc = start_script('/home/barba_negra/SolarServer/backend/load.py')
            graph_proc = start_script('/home/barba_negra/SolarServer/backend/graficas_insolacion.py')
        logger.info("Ejecutando load.py, ETL detenido")
        time.sleep(60)  # Espera un minuto para evitar múltiples ejecuciones

    # 00:00 - Detener LOAD y arrancar ETL
    elif hour == 00 and minute == 00:
        if load_proc:
            stop_script(load_proc)   
            load_proc = None
        if not etl_proc or etl_proc.poll() is not None:
            etl_proc = start_script('/home/barba_negra/SolarServer/backend/etl.py')
            etl_proc = start_script('/home/barba_negra/SolarServer/backend/endpoint.py')
        logger.info("Ejecutando etl.py, LOAD detenido")
        time.sleep(60)  # Espera un minuto para evitar múltiples ejecuciones

    # Si no hay nada corriendo (por ejemplo, al iniciar el script), arranca ETL por defecto
    elif not etl_proc and not endpoint_proc and (not load_proc or load_proc.poll() is not None):
        ensure_services()
        logger.info("Servicios iniciados por defecto")
        email_alert.notificacion("Estación iniciada", "La estación solarimétrica se ha iniciado correctamente")

    time.sleep(10)  # Checa cada 10 segundos
