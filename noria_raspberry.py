# noria_raspberry.py
# EJECUTAR DEPENDENCIAS EN LA RASPBERRY:
"""
sudo apt update
sudo apt install python3-pip
pip3 install paho-mqtt RPi.GPIO

"""


import time
import json
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO

# ---------------- CONFIGURACIÓN ----------------
BROKER = "broker.hivemq.com"   # Puedes cambiarlo por tu propio broker
PORT = 1883
TOPIC_CONTROL = "noria/control/#"   # Escucha todos los comandos de control
TOPIC_ESTADO = "noria/estado"       # Publica estados
CLIENT_ID = "RaspberryNoria"

# --- Pines GPIO (ajústalos según tu circuito real) ---
PIN_MOTOR = 17
PIN_LUCES = 27
PIN_MUSICA = 22

# Inicialización de GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_MOTOR, GPIO.OUT)
GPIO.setup(PIN_LUCES, GPIO.OUT)
GPIO.setup(PIN_MUSICA, GPIO.OUT)

# PWM para controlar la velocidad del motor
motor_pwm = GPIO.PWM(PIN_MOTOR, 100)
motor_pwm.start(0)

# Variables de estado
estado_motor = False
estado_luces = False
estado_musica = False
velocidad_actual = 0

# ---------------------------------------------------
def publicar_estado(client):
    """Publica periódicamente el estado actual de la Noria."""
    estado = {
        "motor": estado_motor,
        "luces": estado_luces,
        "musica": estado_musica,
        "velocidad": velocidad_actual
    }
    client.publish(f"{TOPIC_ESTADO}/general", json.dumps(estado))
    print("📤 Estado publicado:", estado)

# ---------------------------------------------------
def on_connect(client, userdata, flags, rc):
    print("🔗 Conectado al broker MQTT con código:", rc)
    client.subscribe(TOPIC_CONTROL)
    client.publish(f"{TOPIC_ESTADO}/conexion", "Raspberry conectada ✅")

def on_message(client, userdata, msg):
    global estado_motor, estado_luces, estado_musica, velocidad_actual

    topic = msg.topic
    payload = msg.payload.decode()
    print(f"📩 Mensaje recibido: {topic} -> {payload}")

    try:
        # --- Control del motor ---
        if "motor" in topic:
            estado_motor = payload in ("1", "true", "True")
            GPIO.output(PIN_MOTOR, GPIO.HIGH if estado_motor else GPIO.LOW)
            client.publish(f"{TOPIC_ESTADO}/motor", "Encendido" if estado_motor else "Apagado")

        # --- Control de luces ---
        elif "luces" in topic:
            try:
                # Puede venir JSON con colores de ChatGPT
                data = json.loads(payload)
                if "colors" in data:
                    estado_luces = True
                    print("🎨 Colores recibidos:", data["colors"])
                else:
                    estado_luces = payload in ("1", "true", "True")
            except json.JSONDecodeError:
                estado_luces = payload in ("1", "true", "True")

            GPIO.output(PIN_LUCES, GPIO.HIGH if estado_luces else GPIO.LOW)
            client.publish(f"{TOPIC_ESTADO}/luces", "Encendido" if estado_luces else "Apagado")

        # --- Control de música ---
        elif "musica" in topic:
            estado_musica = payload in ("1", "true", "True")
            GPIO.output(PIN_MUSICA, GPIO.HIGH if estado_musica else GPIO.LOW)
            client.publish(f"{TOPIC_ESTADO}/musica", "Encendida" if estado_musica else "Apagada")

        # --- Control de velocidad ---
        elif "velocidad" in topic:
            try:
                velocidad_actual = int(payload)
                motor_pwm.ChangeDutyCycle(velocidad_actual)
                client.publish(f"{TOPIC_ESTADO}/velocidad", str(velocidad_actual))
            except ValueError:
                print("⚠️ Valor de velocidad no válido:", payload)

    except Exception as e:
        print("⚠️ Error procesando mensaje:", e)

# ---------------------------------------------------
def main():
    client = mqtt.Client(CLIENT_ID)
    client.on_connect = on_connect
    client.on_message = on_message

    # Si usas autenticación:
    # client.username_pw_set("usuario", "contraseña")

    client.connect(BROKER, PORT, 60)
    client.loop_start()

    try:
        while True:
            publicar_estado(client)
            time.sleep(5)  # publica cada 5 segundos
    except KeyboardInterrupt:
        print("🛑 Finalizando programa...")
    finally:
        GPIO.cleanup()
        client.loop_stop()
        client.disconnect()

# ---------------------------------------------------
if __name__ == "__main__":
    main()
