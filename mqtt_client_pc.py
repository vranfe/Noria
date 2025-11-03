import paho.mqtt.client as mqtt
import threading

class MQTTClientPC:
    """
    Cliente MQTT para la PC que maneja la interfaz Tkinter.
    Se conecta al broker y comunica los estados entre la interfaz y la Raspberry.
    """

    def __init__(self, broker, port, topic_estado, topic_control, on_message_callback=None):
        self.broker = broker
        self.port = port
        self.topic_estado = topic_estado
        self.topic_control = topic_control
        self.on_message_callback = on_message_callback

        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self._on_message_wrapper

    def on_connect(self, client, userdata, flags, rc):
        print(f"🔗 Conectado al broker MQTT ({self.broker}:{self.port}) con código {rc}")
        self.client.subscribe(self.topic_estado)

    def _on_message_wrapper(self, client, userdata, msg):
        if self.on_message_callback:
            # Llamamos la función que se definió desde la interfaz principal
            self.on_message_callback(msg.topic, msg.payload.decode())

    def connect(self):
        try:
            self.client.connect(self.broker, self.port, 60)
            threading.Thread(target=self.client.loop_forever, daemon=True).start()
        except Exception as e:
            print("❌ Error al conectar con el broker:", e)

    def publish(self, topic, message):
        print(f"📤 Publicando en {topic} -> {message}")
        try:
            self.client.publish(topic, message)
        except Exception as e:
            print("⚠️ Error al publicar:", e)
