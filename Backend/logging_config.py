import logging
from logging.handlers import RotatingFileHandler
import os

LOG_DIR = os.path.join('/home/barba_negra/data', 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'solarserver.log')

def configurar_logging(level=logging.INFO, maxBytes=5*1024*1024, backupCount=5):
    """Configura el logging con un archivo rotativo y salida a consola."""
    os.makedirs(LOG_DIR, exist_ok=True)

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    # Archivo rotativo
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=maxBytes, backupCount=backupCount)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    # Console handler
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(level)

    root = logging.getLogger()
    # If already configured, don't add duplicate handlers
    if not any(isinstance(h, RotatingFileHandler) and getattr(h, 'baseFilename', None) == LOG_FILE for h in root.handlers):
        root.setLevel(level)
        root.addHandler(file_handler)
        root.addHandler(console)
