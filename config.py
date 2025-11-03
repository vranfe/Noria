"""
config.py
----------------------------------------
Archivo de configuración general del proyecto "Control de la Noria 🎡".
Contiene las variables globales de conexión MQTT y API de ChatGPT.
----------------------------------------
"""

import os


#  CONFIGURACIÓN MQTT

# --- Broker MQTT ---
MQTT_BROKER = os.getenv("MQTT_BROKER", "broker.hivemq.com")  # Broker público por defecto
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))              # Puerto estándar sin TLS (8883 si usas SSL)
MQTT_USER = ""                      # Usuario (si tu broker requiere autenticación)
MQTT_PASSWORD = ""              # Contraseña (idem)

# --- Tópicos base ---
TOPIC_BASE = "noria"
TOPIC_CONTROL = f"{TOPIC_BASE}/control"   # Ejemplo: noria/control/motor
TOPIC_ESTADO = f"{TOPIC_BASE}/estado"     # Ejemplo: noria/estado/velocidad

# --- Otras configuraciones ---
USE_TLS = os.getenv("MQTT_USE_TLS", "false").lower() in ("1", "true", "yes")
QOS = 1  # Nivel de calidad de servicio para MQTT (0, 1 o 2)



#  CONFIGURACIÓN DE LA API DE CHATGPT (OpenAI)


# Clave de API: puedes definirla como variable de entorno o colocarla directamente aquí.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Si deseas usar otra API o modelo distinto, cambia estos valores:
CHATGPT_MODEL = os.getenv("CHATGPT_MODEL", "gpt-3.5-turbo")
CHATGPT_TEMPERATURE = float(os.getenv("CHATGPT_TEMPERATURE", "0.8"))



