"""
config.py
----------------------------------------
Versión orientada a objetos del archivo de configuración
para el proyecto "Control de la Noria 🎡".
----------------------------------------
"""

import os


# ============================================================
# Clase: MQTTConfig
# ============================================================
class MQTTConfig:
    """Configuración del cliente MQTT y sus tópicos."""

    def __init__(self):
        # Broker
        self.BROKER = os.getenv("MQTT_BROKER", "broker.hivemq.com")
        self.PORT = int(os.getenv("MQTT_PORT", "1883"))
        self.USER = os.getenv("MQTT_USER", "")
        self.PASSWORD = os.getenv("MQTT_PASSWORD", "")

        # Tópicos
        self.TOPIC_BASE = "noria"
        self.TOPIC_CONTROL = f"{self.TOPIC_BASE}/control"
        self.TOPIC_ESTADO = f"{self.TOPIC_BASE}/estado"

        # Parámetros adicionales
        self.USE_TLS = os.getenv("MQTT_USE_TLS", "false").lower() in ("1", "true", "yes")
        self.QOS = int(os.getenv("MQTT_QOS", "1"))

    def resumen(self):
        """Devuelve un resumen legible de la configuración actual."""
        return {
            "Broker": self.BROKER,
            "Puerto": self.PORT,
            "TLS": self.USE_TLS,
            "QOS": self.QOS,
            "Tópico control": self.TOPIC_CONTROL,
            "Tópico estado": self.TOPIC_ESTADO,
        }


# ============================================================
# Clase: OpenAIConfig
# ============================================================
class OpenAIConfig:
    """Configuración para el uso de la API de ChatGPT (OpenAI)."""

    def __init__(self):
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        self.MODEL = os.getenv("CHATGPT_MODEL", "gpt-3.5-turbo")
        self.TEMPERATURE = float(os.getenv("CHATGPT_TEMPERATURE", "0.8"))

    def resumen(self):
        """Devuelve un resumen legible de la configuración de OpenAI."""
        return {
            "Modelo": self.MODEL,
            "Temperatura": self.TEMPERATURE,
            "API_KEY definida": bool(self.OPENAI_API_KEY),
        }


# ============================================================
# Clase: AppConfig (contenedora general)
# ============================================================
class AppConfig:
    """Clase principal que agrupa todas las configuraciones del proyecto."""

    def __init__(self):
        self.mqtt = MQTTConfig()
        self.openai = OpenAIConfig()

    def resumen(self):
        """Muestra ambas configuraciones de manera resumida."""
        return {
            "MQTT": self.mqtt.resumen(),
            "OpenAI": self.openai.resumen()
        }







