# 🌞 Sistema Automatizado de Adquisición de Datos Solarimétricos

Prototipo de un sistema automatizado para la adquisición, procesamiento y visualización de datos solarimétricos en Cancún, Quintana Roo.

**Proyecto Terminal** - Ingeniería en Datos e Inteligencia Organizacional | Ingeniería Ambiental con especialidad en Energías Renovables

---

## 📋 Tabla de Contenidos

- [Descripción del Proyecto](#descripción-del-proyecto)
- [Características](#características)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Uso](#uso)
- [Especificaciones Técnicas](#especificaciones-técnicas)
- [Autores](#autores)
- [Licencia](#licencia)

---

## 📖 Descripción del Proyecto

Este repositorio contiene toda la documentación, código y especificaciones de hardware necesarias para un sistema completo de monitoreo solar. El sistema realiza la adquisición automática de datos solarimétricos, procesamiento en tiempo real (ETL), y visualización mediante un dashboard interactivo en Dash.

### Objetivos

- ✅ Automatizar la adquisición de datos solarimétricos
- ✅ Procesar y almacenar datos de forma eficiente
- ✅ Visualizar datos en tiempo real mediante dashboard web
- ✅ Generar alertas automáticas por anomalías
- ✅ Mantener historial completo de mediciones

---

## ⭐ Características

- **Backend robusto**: Servidor Python con ETL automático, MQTT y API REST
- **Frontend interactivo**: Dashboard en tiempo real con Dash
- **Microcontroladores**: Firmware especializado para ESP32 y Arduino
- **Múltiples sensores**: Piranómetros, termopares y sensores ambientales
- **Logging centralizado**: Sistema de logs con rotación automática
- **Alertas por email**: Notificación de anomalías en tiempo real
- **Simulación**: Modo simulador para pruebas sin hardware

---

## 📁 Estructura del Proyecto

```
Estacion-solarimetrica-automatizada/
├── Backend/                          # Servidor Python
│   ├── main.py                      # Gestor principal de procesos
│   ├── endpoint.py                  # API REST
│   ├── etl.py                       # Procesamiento de datos
│   ├── load.py                      # Carga a base de datos
│   ├── email_alert.py               # Sistema de alertas por email
│   ├── graficas_insolacion.py       # Generación de gráficos
│   ├── logging_config.py            # Configuración de logs
│   └── simulador.py                 # Simulador de datos
├── Frontend/                         # Interfaz web
│   └── app.py                       # Dashboard Dash
├── Modulos/                          # Hardware y Firmware
│   ├── Ambiental/                   # Módulo de temperatura/humedad
│   │   ├── Firmware/
│   │   │   ├── Arduino_dht/
│   │   │   └── ESP32_sht/
│   │   └── PCB/
│   ├── Datalogger/                  # Módulo datalogger
│   │   ├── Firmware/
│   │   │   ├── Datalogger/
│   │   │   ├── Datalogger_V2/
│   │   │   ├── Datalogger_V3/
│   │   │   └── Datalogger_V4/
│   │   └── PCB/
│   └── Termopares/                  # Módulo termopares
│       ├── Firmware/
│       │   └── Arduino_termo/
|       |   |__ ESP32_termo/
│       └── PCB/
├── LICENSE
└── README.md
```

---

## 💻 Instalación

### Requisitos Previos

- **Python 3.13** o superior
- **Mosquitto Broker** para comunicación MQTT
- **pip** (gestor de paquetes de Python)

### Paso 1: Clonar el Repositorio

```bash
git clone https://github.com/Alejandro1050/Estacion-solarimetrica-automatizada.git
cd Estacion-solarimetrica-automatizada
```

### Paso 2: Instalar Mosquitto Broker

```bash
# En sistemas Debian/Ubuntu
sudo apt update
sudo apt install mosquitto mosquitto-clients

# Iniciar el servicio
sudo systemctl start mosquitto
sudo systemctl enable mosquitto
```

### Paso 3: Instalar Dependencias Python

```bash
# Crear entorno virtual (recomendado)
python3 -m venv venv
source venv/bin/activate

# Instalar paquetes
pip3 install -r requirements.txt
```

### Paso 4: Cargar Firmware en Microcontroladores

1. **Datalogger**: Usar Arduino IDE para cargar `Modulos/Datalogger/Firmware/Datalogger_V4/Datalogger_V4.ino`
2. **Módulo Ambiental**: Cargar `Modulos/Ambiental/Firmware/ESP32-Ambi/ESP32-Ambi.ino`
3. **Termopares**: Cargar `Modulos/Termopares/Firmware/Termocuplas/Termocuplas.ino`

---

## ⚙️ Configuración

### Ubicación Geográfica

Ubicación instalada en Cancún, Quintana Roo:

| Parámetro | Valor |
|-----------|-------|
| **Latitud** | 21°54'07" N |
| **Longitud** | 86°49'48" O |
| **Altura** | 6 m sobre el nivel del mar |
| **Zona horaria** | America/Cancun (UTC-6, UTC-5 con DST) |

### Configuración de Piranómetros

El sistema cuenta con dos piranómetros de precisión estándar (SPP):

| Sensor | Modelo | Constante Calibración | Canal Datalogger | Medición |
|--------|--------|----------------------|-------------------|----------|
| **Piranómetro 1** | SPP | 8.66 µV/(W/m²) | Canal 1 | DHI (Irradiancia Horizontal Difusa) |
| **Piranómetro 2** | SPP | 8.72 µV/(W/m²) | Canal 2 | GHI (Irradiancia Horizontal Global) |

### Variables Medidas

El sistema recopila las siguientes variables:

- **DHI**: Irradiancia Horizontal Difusa (W/m²)
- **GHI**: Irradiancia Horizontal Global (W/m²)
- **DNI**: Irradiancia Normal Directa (W/m²) - calculada
- **Temperatura 1**: Termocupla 1 (°C)
- **Temperatura 2**: Termocupla 2 (°C)
- **Temperatura Ambiente**: Sensor SHT31 (°C)
- **Humedad Ambiente**: Sensor SHT31 (%)
- **Ángulo Cenital Solar**: Calculado en tiempo real (°)

---

## 🚀 Uso

### Iniciar el Sistema Completo

```bash
# Con entorno virtual activado
cd Backend
python3 main.py
```

Esto inicia automáticamente:
- ETL (procesamiento de datos)
- Endpoint API (disponible en `http://localhost:5001`)
- Frontend (dashboard disponible en `http://localhost:8050`)

### Ejecutar Componentes de Forma Independiente

**Solo Backend (API + ETL)**:
```bash
cd Backend
python3 main.py
```

**Solo Frontend (Dashboard)**:
```bash
cd Frontend
python3 app.py
```

**Modo Simulador** (para pruebas sin hardware):
```bash
cd Backend
python3 simulador.py
```

### Acceder al Dashboard

Una vez iniciado el sistema, abre tu navegador en:

```
http://localhost:8050
```

El dashboard te permite:
- Ver gráficos en tiempo real
- Consultar historial de datos
- Monitorear alertas
- Descargar datos

---

## 🔧 Especificaciones Técnicas

### Stack Tecnológico

**Backend:**
- Python 3.13
- Flask/API REST
- MQTT (Mosquitto)
- Polars para procesamiento de datos

**Frontend:**
- Dash (Plotly)
- Bootstrap para UI
- WebSocket para tiempo real

**Hardware:**
- ESP32-C3 para adquisición
- Piranómetros SPP
- Termopares tipo K
- Sensor SHT31

### Comunicación

- **MQTT**: Comunicación en tiempo real con sensores (puerto 1883)
- **REST API**: Acceso a datos históricos (puerto 5001)
- **HTTP**: Dashboard web (puerto 8050)

## 📊 Funcionalidades Principales

### ETL (Extract, Transform, Load)
- Extrae datos de MQTT en tiempo real
- Transforma y valida mediciones
- Calcula variables derivadas (DNI, ángulo zenital)
- Carga en base de datos

### Alertas
- Detección de anomalías automática
- Notificaciones por email
- Histórico de alertas

### Visualización
- Gráficos interactivos en tiempo real
- Análisis histórico
- Exportación de datos

---

## 🐛 Troubleshooting

**El dashboard no se conecta:**
- Verificar que Mosquitto está corriendo: `systemctl status mosquitto`
- Verificar logs: `tail -f data/logs/solarserver.log`

**Error de conexión MQTT:**
- Reiniciar Mosquitto: `sudo systemctl restart mosquitto`
- Verificar firewall: `sudo ufw allow 1883`

**API no responde:**
- Verificar que endpoint.py está ejecutándose
- Revisar puerto 5001: `lsof -i :5001`

---

## 📝 Licencia

Este proyecto está licenciado bajo [ver LICENSE](./LICENSE)

---

## 👥 Autores

Mel josé Cahuich Garcia - ing. ambiental 

Correo: 200300847@ucaribe.edu.mx

Carlos Alejandro Cordova Cocom - Ing. en datos e inteligencia organizacional

correo: 200300617@ucaribe.edu.mx

Nayeli Pérez Tun - Ing. ambiental 

correo: 200300850@ucaribe.edu.mx

Paola Ariana Tut Cupul - Ing. ambiental 

correo: 200300832@ucaribe.edu.mx

---

## 📞 Soporte

Para reportar problemas o sugerencias, crea un [issue](https://github.com/Alejandro1050/Estacion-solarimetrica-automatizada/issues) en el repositorio.

---

**Última actualización**: 27 de noviembre de 2025

