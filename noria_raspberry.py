"""
noria_raspberry.py
----------------------------------------
Versión orientada a objetos del programa principal
para controlar la Noria 🎡 desde la Raspberry Pi.

Requisitos:
sudo apt update
sudo apt install python3-pip
pip3 install paho-mqtt RPi.GPIO
----------------------------------------
"""

import time
import json
import threading
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
from config import AppConfig


class NoriaRaspberry:
    """Clase principal que controla la noria mediante MQTT y pines GPIO."""

    def __init__(self, config: AppConfig):
        # Configuración general (MQTT, pines, etc.)
        self.config = config.mqtt

        # Pines GPIO
        self.PIN_MOTOR = 17
        self.PIN_LUCES = 27
        self.PIN_MUSICA = 22

        # Estado actual
        self.estado_motor = False
        self.estado_luces = False
        self.estado_musica = False
        self.velocidad_actual = 0

        # Configurar GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.PPIN_MOTOR, GPIO.OUT)
        GPIO.setup(self.PIN_LUCES, GPIO.OUT)
        GPIO.setup(self.PIN_MUSICA, GPIO.OUT)

        # PWM para el motor
        self.motor_pwm = GPIO.PWM(self.PIN_MOTOR, 100)
        self.motor_pwm.start(0)

        # Cliente MQTT
        self.client = mqtt.Client("RaspberryNoria")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.connect(self.config.BROKER, self.config.PORT, 60)

        # Hilo para el loop MQTT
        threading.Thread(target=self.client.loop_forever, daemon=True).start()

        print("🎡 Noria Raspberry iniciada correctamente.")

    # ======================================================
    # MQTT Callbacks
    # ======================================================
    def _on_connect(self, client, userdata, flags, rc):
        """Callback al conectarse al broker."""
        if rc == 0:
            print(f"✅ Conectado al broker {self.config.BROKER}:{self.config.PORT}")
            client.subscribe(f"{self.config.TOPIC_BASE}/control/#")
            client.publish(f"{self.config.TOPIC_ESTADO}/conexion", "Raspberry conectada ✅")
        else:
            print(f"⚠️ Error al conectar con el broker MQTT (código {rc})")

    def _on_message(self, client, userdata, msg):
        """Procesa los mensajes de control recibidos."""
        topic = msg.topic
        payload = msg.payload.decode()
        print(f"📩 Mensaje recibido: {topic} -> {payload}")

        try:
            if "motor" in topic:
                self._control_motor(payload)
            elif "luces" in topic:
                self._control_luces(payload)
            elif "musica" in topic:
                self._control_musica(payload)
            elif "velocidad" in topic:
                self._control_velocidad(payload)
            else:
                print(f"⚠️ Tópico desconocido: {topic}")
        except Exception as e:
            print("⚠️ Error procesando mensaje:", e)

    # ======================================================
    # Controles individuales
    # ======================================================
    def _control_motor(self, payload):
        self.estado_motor = payload in ("1", "true", "True")
        GPIO.output(self.PIN_MOTOR, GPIO.HIGH if self.estado_motor else GPIO.LOW)
        estado_texto = "Encendido" if self.estado_motor else "Apagado"
        self.client.publish(f"{self.config.TOPIC_ESTADO}/motor", estado_texto)
        print(f"🌀 Motor {estado_texto}")

    def _control_luces(self, payload):
        try:
            data = json.loads(payload)
            if "colors" in data:
                self.estado_luces = True
                print("🎨 Colores recibidos:", data["colors"])
            else:
                self.estado_luces = payload in ("1", "true", "True")
        except json.JSONDecodeError:
            self.estado_luces = payload in ("1", "true", "True")

        GPIO.output(self.PIN_LUCES, GPIO.HIGH if self.estado_luces else GPIO.LOW)
        estado_texto = "Encendidas" if self.estado_luces else "Apagadas"
        self.client.publish(f"{self.config.TOPIC_ESTADO}/luces", estado_texto)
        print(f"💡 Luces {estado_texto}")

    def _control_musica(self, payload):
        self.estado_musica = payload in ("1", "true", "True")
        GPIO.output(self.PIN_MUSICA, GPIO.HIGH if self.estado_musica else GPIO.LOW)
        estado_texto = "Encendida" if self.estado_musica else "Apagada"
        self.client.publish(f"{self.config.TOPIC_ESTADO}/musica", estado_texto)
        print(f"🎵 Música {estado_texto}")

    def _control_velocidad(self, payload):
        try:
            self.velocidad_actual = int(payload)
            self.motor_pwm.ChangeDutyCycle(self.velocidad_actual)
            self.client.publish(f"{self.config.TOPIC_ESTADO}/velocidad", str(self.velocidad_actual))
            print(f"⚙️ Velocidad ajustada a {self.velocidad_actual}%")
        except ValueError:
            print("⚠️ Valor de velocidad no válido:", payload)

    # ======================================================
    # Estado general
    # ======================================================
    def publicar_estado(self):
        """Publica el estado actual de todos los actuadores."""
        estado = {
            "motor": self.estado_motor,
            "luces": self.estado_luces,
            "musica": self.estado_musica,
            "velocidad": self.velocidad_actual
        }
        self.client.publish(f"{self.config.TOPIC_ESTADO}/general", json.dumps(estado))
        print("📤 Estado publicado:", estado)

    # ======================================================
    # Ejecución principal
    # ======================================================
    def run(self):
        """Inicia el ciclo principal de publicación de estados."""
        try:
            while True:
                self.publicar_estado()
                time.sleep(5)
        except KeyboardInterrupt:
            print("🛑 Finalizando programa...")
            self._cleanup()

    def _cleanup(self):
        """Limpieza final de recursos GPIO y MQTT."""
        GPIO.cleanup()
        self.client.disconnect()
        print("🔌 Recursos liberados correctamente.")


# ======================================================
# Ejecución directa
# ======================================================
if __name__ == "__main__":
    app_config = AppConfig()
    noria = NoriaRaspberry(app_config)
    noria.run()
