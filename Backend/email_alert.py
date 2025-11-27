import logging
import smtplib
from email.message import EmailMessage
from datetime import datetime
from typing import List

# Configuración
logger = logging.getLogger(__name__)

# Configuración de email
EMAIL_CONFIG = {
    'sender': "estacionsolarimetrica@gmail.com",
    'recipients': [
        "200300617@ucaribe.edu.mx",  # Alejandro
        "200300847@ucaribe.edu.mx",  # Mel José
        "200300850@ucaribe.edu.mx",  # Nayeli
        "200300832@ucaribe.edu.mx"   # Ariana
    ],
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'password': "kvzz jipv oepi cuwz"
}

def _create_email_message(subject: str, body: str, recipient: str) -> EmailMessage:
    """Crea un mensaje de email individual."""
    message = EmailMessage()
    message.set_content(body)
    message['Subject'] = subject
    message['From'] = EMAIL_CONFIG['sender']
    message['To'] = recipient
    return message

def _send_emails(messages: List[EmailMessage]) -> None:
    """Envía una lista de mensajes de email usando una sola conexión SMTP."""
    try:
        with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.starttls()
            server.login(EMAIL_CONFIG['sender'], EMAIL_CONFIG['password'])
            
            for message in messages:
                try:
                    server.send_message(message)
                except Exception as e:
                    logger.error("Error al enviar el correo a %s: %s", message['To'], e)
                    continue
    except Exception as e:
        logger.error("Error al conectar con el servidor SMTP: %s", e)

def _prepare_emails(subject: str, body_template: str, **kwargs) -> List[EmailMessage]:
    """Prepara los mensajes de email para todos los destinatarios."""
    time = datetime.now().strftime("%H:%M:%S")
    body = body_template.format(time=time, **kwargs)
    
    messages = []
    for recipient in EMAIL_CONFIG['recipients']:
        message = _create_email_message(subject, body, recipient)
        messages.append(message)
    
    return messages

def error_alert(modulo: str, subject: str) -> None:
    """Envía alerta de error en un módulo."""
    body_template = f"Error en módulo {modulo} a las {{time}} hrs."
    messages = _prepare_emails(subject, body_template, modulo=modulo)
    _send_emails(messages)

def carga_error(nombre: str) -> None:
    """Envía alerta de error en carga de archivo."""
    subject = "Error en carga de archivo"
    body_template = f"Error en la carga del archivo {nombre} a las {{time}} hrs."
    messages = _prepare_emails(subject, body_template, nombre=nombre)
    _send_emails(messages)

def carga_ok(nombre: str) -> None:
    """Envía notificación de carga exitosa."""
    subject = "Archivo cargado"
    body_template = f"Archivo {nombre} correctamente cargado a las {{time}} hrs."
    messages = _prepare_emails(subject, body_template, nombre=nombre)
    _send_emails(messages)

def notificacion(subject: str, body: str) -> None:
    """Envía una notificación general."""
    body_template = f"{body} a las {{time}} hrs."
    messages = _prepare_emails(subject, body_template)
    _send_emails(messages)