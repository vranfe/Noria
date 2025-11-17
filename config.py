import os

# ============================================================
# Clase: MQTTConfig
# ============================================================
class MQTTConfig:
    def __init__(self):
        self.BROKER = "broker.hivemq.com"
        self.PORT = 1883
        self.USER = ""
        self.PASSWORD = ""

        self.TOPIC_BASE = "noria"
        self.TOPIC_CONTROL = f"{self.TOPIC_BASE}/control"
        self.TOPIC_ESTADO = f"{self.TOPIC_BASE}/estado"

        self.USE_TLS = False
        self.QOS = 1

    def resumen(self):
        return {
            "Broker": self.BROKER,
            "Puerto": self.PORT,
            "TLS": self.USE_TLS,
            "QOS": self.QOS,
            "Tópico control": self.TOPIC_CONTROL,
            "Tópico estado": self.TOPIC_ESTADO,
        }


# ============================================================
# Clase: GeminiConfig
# ============================================================
class GeminiConfig:
    """Configuración para la API de Gemini."""
    def __init__(self, api_key=None):

        # NOTA: En una aplicación real, no se debería hardcodear la API key
        # y se debería obtener de una variable de entorno como os.environ.get("GEMINI_API_KEY")
        self.GEMINI_API_KEY = (
            api_key
            or os.environ.get("GEMINI_API_KEY", "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") # Usar variable de entorno si existe
        )
        
        # MODELO CORREGIDO: Usar el nombre corto y actual.
        self.MODEL = "gemini-1.5-flash" 

        self.TEMPERATURE = 0.3

    def resumen(self):
        return {
            "Modelo": self.MODEL,
            "Temperatura": self.TEMPERATURE,
            "API_KEY definida": bool(self.GEMINI_API_KEY),
        }


# ============================================================
# Clase principal
# ============================================================
class AppConfig:
    def __init__(self):
        self.mqtt = MQTTConfig()
        # Pasar explícitamente la API key si se desea inicializar desde el entorno
        self.gemini = GeminiConfig()

# Si quieres usar un solo objeto de configuración global:
app_config = AppConfig()








