import os
import sys
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError, ResumableUploadError
import email_alert

# --- Configuración ---
# Define los ámbitos de acceso. 'https://www.googleapis.com/auth/drive' permite
# acceso completo a los archivos del usuario que otorgue permisos.
SCOPES = ['https://www.googleapis.com/auth/drive']

# Reemplaza 'ruta/a/tus-credenciales.json' con la ruta real de tu archivo de credenciales.
# Es una buena práctica usar una variable de entorno en un servidor para mayor seguridad.
# Por ejemplo: credenciales_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
CREDENTIALS_PATH = '/home/barba_negra/Plataforma-MQTT/backend/quantum-transit-454701-t9-1072bdae8e6e.json'

# Reemplaza 'ruta/de/mi/carpeta/local' con la ruta a tu carpeta local.
LOCAL_FOLDER = '/home/barba_negra/data'

# Reemplaza 'ID_DE_LA_CARPETA_DE_DRIVE' con el ID de tu carpeta de Google Drive.
#DRIVE_FOLDER_ID = '1NMFSUC9MUqCHba2kuUxi5eCac8ZMAuXt'
DRIVE_FOLDER_ID="1VDvTAz6mSl3Pdbn4T0CL52o68-i0dqpB"
# --- Funciones de Ayuda ---

def authenticate():
    """
    Autentica la aplicación utilizando el archivo de credenciales del servicio de Google.

    Returns:
        objeto 'service' de la API de Google Drive.
    """
    try:
        creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        print("Autenticación exitosa.")
        return service
    except FileNotFoundError:
        print(f"Error: El archivo de credenciales no se encontró en '{CREDENTIALS_PATH}'.")
        email_alert.carga_error("Archivo de credenciales no encontrado.")
        sys.exit(1)
    except Exception as e:
        print(f"Error durante la autenticación: {e}")
        email_alert.carga_error(f"Error de autenticación: {e}")
        sys.exit(1)

def file_exists_on_drive(service, filename, folder_id):
    try:
        query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
        results = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name)",
            includeItemsFromAllDrives=True,  
            supportsAllDrives=True           
        ).execute()
        items = results.get('files', [])
        if items:
            print(f"Archivo '{filename}' ya existe en Drive con ID: {items[0]['id']}.")
            return items[0]['id']
        return None
    except HttpError as error:
        print(f"Error al verificar la existencia del archivo: {error}")
        return None

def upload_file(service, filepath, drive_folder_id):
    """
    Sube un archivo local a Google Drive. Si ya existe, lo omite.

    Args:
        service: El objeto de servicio de la API de Google Drive.
        filepath (str): La ruta completa del archivo local.
        drive_folder_id (str): El ID de la carpeta de Google Drive de destino.
    """
    filename = os.path.basename(filepath)
    print(f"Procesando el archivo: {filename}")

    # Paso 1: Verificar si el archivo ya existe en Google Drive
    existing_file_id = file_exists_on_drive(service, filename, drive_folder_id)
    if existing_file_id:
        print(f"Archivo '{filename}' ya existe. Saltando la subida.")
        return

    # Paso 2: Subir el archivo si no existe
    file_metadata = {
        'name': filename,
        'parents': [drive_folder_id]
    }
    
    media = MediaFileUpload(filepath)
    
    try:
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id',
            supportsAllDrives=True  # Necesario para crear archivos en unidades compartidas
        ).execute()
        print(f"Archivo '{filename}' subido exitosamente con ID: {file.get('id')}")
        email_alert.carga_ok(filename)
    except ResumableUploadError as error:
        print(f"Error de subida resumible para '{filename}': {error}")
        email_alert.carga_error(filename)
    except HttpError as error:
        print(f"Error de subida para '{filename}': {error}")
        email_alert.carga_error(filename)

def main():
    """
    Función principal que autentica y sube todos los archivos de la carpeta local.
    """
    print("Iniciando el script de subida a Google Drive...")
    service = authenticate()
    
    # Verificar si la carpeta local existe
    if not os.path.isdir(LOCAL_FOLDER):
        print(f"Error: La carpeta local '{LOCAL_FOLDER}' no existe o no es accesible.")
        sys.exit(1)
    
    files_to_upload = os.listdir(LOCAL_FOLDER)
    if not files_to_upload:
        print(f"No se encontraron archivos en la carpeta local '{LOCAL_FOLDER}'.")
        return
    
    for filename in files_to_upload:
        filepath = os.path.join(LOCAL_FOLDER, filename)
        
        # Subir solo si es un archivo regular
        if os.path.isfile(filepath):
            upload_file(service, filepath, DRIVE_FOLDER_ID)
        else:
            print(f"'{filename}' no es un archivo regular, se omitirá.")

    print("\nProceso de subida finalizado.")

if __name__ == '__main__':
    main()
