# interfaz.py
"""
Interfaz gráfica para la Noria (MQTT + ESP32).
- Botones apilados a la izquierda (Motor, Luces, Música, Servo).
- Sliders, Chatbot, Colores y Salir a la derecha.
- SOLUCIÓN DEFINITIVA PARA TAMAÑO DE BOTONES
"""

import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import paho.mqtt.client as mqtt
import threading
import json
import time

# Importar configuración orientada a objetos (tu config.py)
from gemini_api import GeminiColorAPI 
from config import AppConfig
config = AppConfig()
# interfaz.py (Línea 21)
# Pasa el objeto 'config' completo, el cual contiene la API Key y el modelo.
color_gen = GeminiColorAPI(config=config) # ✅ CORREGIDO

# ---------------- TOPICS ESP32 ----------------
TOPIC_NEOPIXEL = "esp32/neopixel"
TOPIC_DC_SPEED = "esp32/dc_speed"            # DC motor speed (0-100)
TOPIC_STEPPER_SPEED = "esp32/stepper_speed"  # Stepper motor speed (0-100)
TOPIC_STEPPER = "esp32/stepper_delay"        # Compatibilidad, si alguien usa delay
TOPIC_SONG = "esp32/play_song"
TOPIC_CHATBOT = "esp32/chatbot_command"
TOPIC_SERVO = "esp32/servo_door"
TOPIC_ERROR = "esp32/error"
TOPIC_STATUS = "esp32/status"
TOPIC_DISTANCE = "esp32/distance_cm"           # Nuevo topic para texto sensor (mostrar en UI)


class InterfazNoria:
    def __init__(self, root):
        self.root = root
        self._configurar_ventana()
        self._definir_colores()

        # MQTT
        self.mqtt_client = None
        self._setup_mqtt()

        # Debounce / últimos enviados
        self._vel_debounce_id = None
        self._vel_last_sent = None
        self._dc_debounce_id = None
        self._dc_last_sent = None


        # Estados
        self.estado_motor = tk.BooleanVar(value=False)   # este controla el stepper (noria)
        self.estado_luces = tk.BooleanVar(value=False)
        self.estado_musica = tk.BooleanVar(value=False)
        self.estado_servo = tk.BooleanVar(value=False)
        self.pasajeros = tk.IntVar(value=0)

        # Traces para mantener UI sincrónica
        self.estado_motor.trace_add("write", lambda *a: self._trace_update("motor"))
        self.estado_luces.trace_add("write", lambda *a: self._trace_update("luces"))
        self.estado_musica.trace_add("write", lambda *a: self._trace_update("musica"))
        self.estado_servo.trace_add("write", lambda *a: self._trace_update("servo"))

        # Bienvenida
        self.frame_bienvenida = tk.Frame(self.root, bg="#FFE5B4")
        self.frame_bienvenida.pack(expand=True, fill="both")
        self._crear_bienvenida()

        # Panel se crea al entrar
        self.panel = None

    def _configurar_ventana(self):
        self.root.title("Control de la Noria 🎡")
        self.root.geometry("1000x650")
        self.root.minsize(900, 550)
        self.root.resizable(True, True)
        self.root.configure(bg="#FFE5B4")
        self.fuente = ("Comic Sans MS", 12, "bold")

    def _definir_colores(self):
        self.COLOR_BASE_APAGADO = "#FFA726"
        self.COLOR_BASE_ENCENDIDO = "#FFB980"
        self.COLOR_TEXTO_APAGADO = "#BF360C"
        self.COLOR_TEXTO_ENCENDIDO = "#E65100"

    def _setup_mqtt(self):
        try:
            self.mqtt_client = mqtt.Client()
            if getattr(config.mqtt, "USER", ""):
                self.mqtt_client.username_pw_set(config.mqtt.USER, config.mqtt.PASSWORD)
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_message = self._on_mqtt_message_internal
            self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
            self.mqtt_client.on_log = self._on_mqtt_log

            print("🔗 Intentando conectar al broker MQTT...", config.mqtt.BROKER, config.mqtt.PORT)
            self.mqtt_client.connect(config.mqtt.BROKER, config.mqtt.PORT, 60)
            self.mqtt_client.loop_start()
        except Exception as e:
            print("⚠️ No se pudo conectar al broker MQTT:", e)
            self.mqtt_client = None

    def _on_mqtt_disconnect(self, client, userdata, rc):
        if rc != 0:
            print("❌ MQTT se desconectó inesperadamente (rc =", rc, ")")
        else:
            print("🔌 MQTT desconectado correctamente.")

    def _on_mqtt_log(self, client, userdata, level, buf):
        if level == mqtt.MQTT_LOG_ERR:
            print("❗ MQTT ERROR:", buf)
        elif level == mqtt.MQTT_LOG_WARNING:
            print("⚠️ MQTT WARNING:", buf)

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        status = "OK" if rc == 0 else f"rc={rc}"
        print("🟢 MQTT conectado exitosamente (", status, ")")
        try:
            # Suscribir a los topics relevantes
            client.subscribe(TOPIC_NEOPIXEL)
            client.subscribe(TOPIC_DC_SPEED)
            client.subscribe(TOPIC_STEPPER_SPEED)
            client.subscribe(TOPIC_STEPPER)
            client.subscribe(TOPIC_SONG)
            client.subscribe(TOPIC_CHATBOT)
            client.subscribe(TOPIC_SERVO)
            client.subscribe(TOPIC_ERROR)
            client.subscribe(TOPIC_STATUS)
            client.subscribe(TOPIC_DISTANCE)
            print("📡 Suscrito a topics esenciales de la noria")
        except Exception as e:
            print("⚠️ Error suscribiendo a topics:", e)

    def _on_mqtt_message_internal(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode(errors="replace")
            self.root.after(0, lambda: self.actualizar_estado(topic, payload))
        except Exception as e:
            print("⚠️ Error en on_message:", e)

    def _mqtt_publish(self, topic, payload):
        try:
            if self.mqtt_client is None:
                print("⚠️ MQTT no inicializado — publicación cancelada.")
                return

            if isinstance(payload, dict):
                if "r" in payload and "g" in payload and "b" in payload:
                    payload = f"{int(payload['r'])},{int(payload['g'])},{int(payload['b'])}"
                elif "colors" in payload and isinstance(payload["colors"], list) and payload["colors"]:
                    trip = payload["colors"][0]
                    payload = f"{int(trip[0])},{int(trip[1])},{int(trip[2])}"
                else:
                    payload = json.dumps(payload)

            print(f"📤 PUBLICAR -> {topic}: {payload}")
            self.mqtt_client.publish(topic, str(payload))
            print("   ✔ Enviado")
        except Exception as e:
            print("❌ Error al publicar MQTT:", e)

    def _crear_bienvenida(self):
        tk.Label(
            self.frame_bienvenida,
            text="🎡 Bienvenido al Control de la Noria 🎡",
            font=("Comic Sans MS", 22, "bold"),
            fg="#FF6F00", bg="#FFE5B4"
        ).pack(pady=60)

        try:
            img = Image.open("assets/logo.png").resize((180, 180))
            self.logo = ImageTk.PhotoImage(img)
            tk.Label(self.frame_bienvenida, image=self.logo, bg="#FFE5B4").pack(pady=10)
        except Exception:
            tk.Label(self.frame_bienvenida, text="(Logo no encontrado)", bg="#FFE5B4", fg="#FF6F00").pack(pady=10)

        tk.Button(
            self.frame_bienvenida, text="Entrar al Panel 🚀",
            command=self.abrir_panel, font=self.fuente,
            bg="#FF854D", fg="white", activebackground="#FF9800",
            relief="flat", width=20, height=2
        ).pack(pady=25)

    def abrir_panel(self):
        print("➡ Abriendo panel de control...")
        try:
            self.frame_bienvenida.destroy()
        except Exception:
            pass
        self._crear_panel_control()

    def _crear_panel_control(self):
        self.panel = tk.Frame(self.root, bg="#FFE5B4")
        self.panel.pack(expand=True, fill="both")

        tk.Label(
            self.panel, text="Panel de Control de la Noria",
            font=("Comic Sans MS", 20, "bold"), bg="#FFE5B4", fg="#E65100"
        ).pack(pady=12)

        # Frame principal para dividir en izquierda y derecha
        main_frame = tk.Frame(self.panel, bg="#FFE5B4")
        main_frame.pack(expand=True, fill="both", padx=20, pady=10)

        # FRAME IZQUIERDO - Botones apilados
        frame_izquierdo = tk.Frame(main_frame, bg="#FFE5B4", width=300)
        frame_izquierdo.pack(side="left", fill="y", padx=(0, 20))
        frame_izquierdo.pack_propagate(False)

        # FRAME DERECHO - Sliders, chatbot, salir
        frame_derecho = tk.Frame(main_frame, bg="#FFE5B4")
        frame_derecho.pack(side="left", expand=True, fill="both")

        # Cargar iconos
        self._cargar_iconos()

        # Título para la sección de controles
        tk.Label(frame_izquierdo, text="Controles Principales", 
                font=("Comic Sans MS", 16, "bold"), bg="#FFE5B4", fg="#E65100").pack(pady=(0, 15))

        # SOLUCIÓN DEFINITIVA: Crear botones con Frame de tamaño fijo
        self._crear_botones_izquierda(frame_izquierdo)
        self._crear_controles_derecha(frame_derecho)

    def _cargar_iconos(self):
        """Cargar todos los iconos necesarios"""
        self.icons = {}
        try:
            icon_size = (28, 28)  # Tamaño uniforme para todos los iconos
            self.icons["motor"] = ImageTk.PhotoImage(Image.open("assets/motor.png").resize(icon_size))
            self.icons["luces"] = ImageTk.PhotoImage(Image.open("assets/luces.png").resize(icon_size))
            self.icons["musica"] = ImageTk.PhotoImage(Image.open("assets/musica.png").resize(icon_size))
            self.icons["salir"] = ImageTk.PhotoImage(Image.open("assets/salir.png").resize(icon_size))
        except Exception as e:
            print(f"⚠️ Error cargando iconos: {e}")

    def _crear_botones_izquierda(self, parent):
        """SOLUCIÓN DEFINITIVA: Crear botones con tamaño fijo usando Frames"""
        # Tamaño fijo para todos los botones
        BOTON_ANCHO = 250
        BOTON_ALTO = 50
        
        # Lista de botones a crear
        botones_config = [
            ("Motor", "motor", self.estado_motor),   # controla el stepper (noria)
            ("Luces", "luces", self.estado_luces),
            ("Música", "musica", self.estado_musica),
            ("Servo", "servo", self.estado_servo)
        ]
        
        for texto, tipo, variable in botones_config:
            # Frame contenedor con tamaño fijo
            frame_boton = tk.Frame(parent, bg="#FFE5B4", width=BOTON_ANCHO, height=BOTON_ALTO)
            frame_boton.pack(pady=8)
            frame_boton.pack_propagate(False)  # ¡IMPORTANTE! Mantener tamaño fijo
            
            # Botón que llena todo el frame
            icon = self.icons.get(tipo)
            btn = tk.Button(
                frame_boton, 
                text=texto, 
                image=icon, 
                compound="left",
                bg=self.COLOR_BASE_APAGADO, 
                fg="white",
                font=self.fuente,
                relief="flat", 
                bd=0, 
                activebackground=self.COLOR_BASE_APAGADO,
                command=lambda t=tipo, v=variable: self._toggle_boton(t, v)
            )
            btn.pack(fill="both", expand=True, padx=2, pady=2)
            
            # Frame para la etiqueta de estado (a la derecha del botón)
            frame_estado = tk.Frame(parent, bg="#FFE5B4", width=80, height=BOTON_ALTO)
            frame_estado.pack_propagate(False)
            frame_estado.pack(pady=8)
            
            # Etiqueta de estado
            if tipo == "servo":
                estado_inicial = "Cerrada" if not variable.get() else "Abierta"
            else:
                estado_inicial = "Apagado" if not variable.get() else "Encendido"
                
            label_estado = tk.Label(
                frame_estado, 
                text=estado_inicial, 
                font=("Comic Sans MS", 10),
                bg="#FFE5B4", 
                fg=self.COLOR_TEXTO_APAGADO,
                anchor="w"
            )
            label_estado.pack(fill="both", expand=True)
            
            # Guardar referencia para actualizaciones
            if not hasattr(self, 'botones_ui'):
                self.botones_ui = {}
            self.botones_ui[tipo] = (btn, label_estado, variable)
            
            # Configurar trace para actualizaciones
            variable.trace_add("write", lambda *args, t=tipo: self._actualizar_ui_boton(t))

    def _crear_controles_derecha(self, parent):
        """Crear controles del lado derecho"""

        # ============================
        # SLIDER VELOCIDAD (STEPPER) - arriba
        # ============================
        velocidad_frame = tk.Frame(parent, bg="#FFE5B4")
        velocidad_frame.pack(fill="x", pady=8)
        # ============================
        # LABEL SENSOR (FALTABA)
        # ============================
        self.label_sensor = tk.Label(parent, text="Sensor: -", font=("Comic Sans MS", 11), bg="#FFE5B4")
        self.label_sensor.pack(anchor="w", pady=6)


        tk.Label(velocidad_frame, text="Velocidad de la Noria (Stepper)", font=self.fuente, bg="#FFE5B4", fg="#BF360C").pack(anchor="w")
        self.velocidad = tk.IntVar(value=50)
        self.scale_vel = tk.Scale(velocidad_frame, from_=0, to=100, orient="horizontal",
                                  variable=self.velocidad, command=self._slider_changed,
                                  length=400, bg="#FFE5B4", fg="#BF360C", troughcolor="#FFD180")
        self.scale_vel.pack(fill="x", pady=5)
        self.label_vel = tk.Label(velocidad_frame, text="Velocidad actual: 50%", font=self.fuente, bg="#FFE5B4", fg="#BF360C")
        self.label_vel.pack(anchor="w")

        # ============================
        # NUEVO BOTÓN MOTOR DC y ETIQUETA DE PASAJEROS (por encima del slider DC)
        # ============================
        BOTON_ANCHO = 250
        BOTON_ALTO = 50

        frame_motor_dc = tk.Frame(parent, bg="#FFE5B4", width=BOTON_ANCHO, height=BOTON_ALTO)
        frame_motor_dc.pack(pady=(8, 6))
        frame_motor_dc.pack_propagate(False)

        btn_motor_dc = tk.Button(
            frame_motor_dc,
            text="Motor DC",
            bg=self.COLOR_BASE_APAGADO,
            fg="white",
            font=self.fuente,
            relief="flat",
            bd=0,
            activebackground=self.COLOR_BASE_APAGADO,
            command=self._toggle_motor_dc
        )
        btn_motor_dc.pack(fill="both", expand=True)
        self.btn_motor_dc = btn_motor_dc

        self.label_pasajeros = tk.Label(parent, text=f"Pasajeros pasaron: {self.pasajeros.get()}", font=self.fuente, bg="#FFE5B4", fg="#BF360C")
        self.label_pasajeros.pack(pady=(0, 12))

        # ============================
        # SLIDER DC (debajo del slider de la noria/stepper)
        # ============================
        dc_frame = tk.Frame(parent, bg="#FFE5B4")
        dc_frame.pack(fill="x", pady=6)

        tk.Label(dc_frame, text="Velocidad Motor DC", font=self.fuente, bg="#FFE5B4", fg="#BF360C").pack(anchor="w")
        self.dc_speed = tk.IntVar(value=50)
        self.scale_dc = tk.Scale(dc_frame, from_=0, to=100, orient="horizontal",
                                 variable=self.dc_speed, command=self._dc_slider_changed,
                                 length=400, bg="#FFE5B4", fg="#BF360C", troughcolor="#FFD180")
        self.scale_dc.pack(fill="x", pady=5)
        self.label_dc = tk.Label(dc_frame, text="DC: 50%", font=self.fuente, bg="#FFE5B4", fg="#BF360C")
        self.label_dc.pack(anchor="w")

        # ============================
        # LABEL DE COLORES
        # ============================
        self.label_colores = tk.Label(parent, text="Colores: -", font=("Comic Sans MS", 11), bg="#FFE5B4")
        self.label_colores.pack(anchor="w", pady=6)

        # ============================
        # CHATBOT (SIN CAMBIOS)
        # ============================
        chatbot_frame = tk.Frame(parent, bg="#FFE5B4")
        chatbot_frame.pack(fill="x", pady=12)

        tk.Label(chatbot_frame, text="Comando Chatbot (envía al ESP):", bg="#FFE5B4").pack(anchor="w")

        entry_frame = tk.Frame(chatbot_frame, bg="#FFE5B4")
        entry_frame.pack(fill="x", pady=5)

        self.chat_entry = tk.Entry(entry_frame, width=40)
        self.chat_entry.pack(side="left", padx=(0, 10))
        tk.Button(entry_frame, text="Enviar comando IA", command=self._send_chatbot_command).pack(side="left")

        # ============================
        # BOTÓN SALIR (INTOCABLE)
        # ============================
        # ============================
        salir_img = self.icons.get("salir")
        tk.Button(
            parent, text="Salir 🚪", command=self._shutdown, font=self.fuente,
            bg="#E64A19", fg="white", activebackground="#BF360C",
            relief="raised", width=15, height=1,
            image=salir_img, compound="left"
        ).pack(pady=20)

    def _toggle_motor_dc(self):
     """
     Toggle del Motor DC.
     Publica SOLO números porque la ESP32 espera un entero:
       - 0 = apagado
       - valor del slider = encendido
     """
     try:
         actual = self.btn_motor_dc.cget("bg")
         nuevo = self.COLOR_BASE_ENCENDIDO if actual == self.COLOR_BASE_APAGADO else self.COLOR_BASE_APAGADO
         self.btn_motor_dc.config(bg=nuevo, activebackground=nuevo)
 
         # Estado ON/OFF
         encendido = (nuevo == self.COLOR_BASE_ENCENDIDO)
 
         # Si está encendido -> enviar la velocidad actual del slider
         # Si está apagado -> enviar 0
         speed_value = int(self.dc_speed.get()) if encendido else 0
 
         print(f"⚡ Toggle DC -> {'ON' if encendido else 'OFF'} (publicando {speed_value})")
 
         # Publicar número simple
         self._mqtt_publish(TOPIC_DC_SPEED, str(speed_value))
 
     except Exception as e:
         print("⚠️ Error en toggle_motor_dc:", e)


    def _toggle_boton(self, tipo, variable_estado):
        """Maneja el clic en cualquier botón"""
        nuevo_estado = not variable_estado.get()
        variable_estado.set(nuevo_estado)
        print(f"🖱 Botón '{tipo}' presionado — nuevo estado: {nuevo_estado}")

        if tipo == "motor":
            # Este botón controla el stepper (noria)
            if nuevo_estado:
                val = self.velocidad.get()
                print(f"⚙️ Publicando velocidad stepper -> {val}%")
                self._mqtt_publish(TOPIC_STEPPER_SPEED, str(val))
            else:
                print("🛑 Publicando detener stepper (0)")
                self._mqtt_publish(TOPIC_STEPPER_SPEED, "0")

        elif tipo == "luces":
            if nuevo_estado:
                print("✨ Solicitando colores IA...")
                if tipo in self.botones_ui:
                    self.botones_ui[tipo][1].config(text="Buscando...", fg=self.COLOR_TEXTO_APAGADO)
                threading.Thread(target=self._worker_luces, daemon=True).start()
            else:
                print("🌑 Publicando apagar luces")
                self._mqtt_publish(TOPIC_NEOPIXEL, "0,0,0")

        elif tipo == "musica":
            if nuevo_estado:
                print(f"🎵 Publicando iniciar música")
                self._mqtt_publish(TOPIC_SONG, "start")
            else:
                print("🔇 Publicando detener música")
                self._mqtt_publish(TOPIC_SONG, "stop")

        elif tipo == "servo":
            if nuevo_estado:
                print("🚪 Publicando Abrir Puerta (Servo)")
                self._mqtt_publish(TOPIC_SERVO, "open")
            else:
                print("🔒 Publicando Cerrar Puerta (Servo)")
                self._mqtt_publish(TOPIC_SERVO, "close")

    def _actualizar_ui_boton(self, tipo):
        """Actualiza la UI del botón cuando cambia su estado"""
        if tipo in self.botones_ui:
            btn, label_estado, variable_estado = self.botones_ui[tipo]
            estado = variable_estado.get()

            if estado:
                btn.config(bg=self.COLOR_BASE_ENCENDIDO, activebackground=self.COLOR_BASE_ENCENDIDO)
                if tipo == "servo":
                    label_estado.config(text="Abierta", fg=self.COLOR_TEXTO_ENCENDIDO)
                else:
                    label_estado.config(text="Encendido", fg=self.COLOR_TEXTO_ENCENDIDO)
            else:
                btn.config(bg=self.COLOR_BASE_APAGADO, activebackground=self.COLOR_BASE_APAGADO)
                if tipo == "servo":
                    label_estado.config(text="Cerrada", fg=self.COLOR_TEXTO_APAGADO)
                else:
                    label_estado.config(text="Apagado", fg=self.COLOR_TEXTO_APAGADO)

    def _worker_luces(self):
     """Worker para manejar la solicitud de colores IA"""
     try:
         data = color_gen.get_colors_from_prompt(
             "Ilumina la noria con colores vibrantes",
             n_colors=3
         )
 
         # Ejemplo esperado:
         # {"colors": [{"r":123,"g":52,"b":255}, ...]}
 
         if not isinstance(data, dict) or "colors" not in data:
             raise ValueError("Formato inesperado de respuesta API")
 
         colors = data["colors"]
         if not isinstance(colors, list) or len(colors) == 0:
             raise ValueError("Lista de colores vacía o inválida")
 
         # --------------------------------------------
         # 🔥 NUEVO: elegir un color aleatorio de la IA
         # --------------------------------------------
         import random
         chosen = random.choice(colors)
 
         # Validar claves
         if not all(k in chosen for k in ("r", "g", "b")):
             raise ValueError("Faltan claves r,g,b en color elegido")
 
         # Convertir a payload "R,G,B"
         payload = f"{chosen['r']},{chosen['g']},{chosen['b']}"
         print(f"🌈 Color elegido por IA -> {payload} (publicando...)")
 
         # Publicar a la Noria (ESP32)
         self._mqtt_publish(TOPIC_NEOPIXEL, payload)
 
         # Mostrar los 3 colores generados en la UI
         colores_str = ", ".join([f"{c['r']},{c['g']},{c['b']}" for c in colors])
         self.root.after(0, lambda: self.label_colores.config(text=f"Colores: {colores_str}"))
 
     except Exception as e:
         print("❌ Error ChatGPT (luces):", e)
         self.root.after(0, lambda: messagebox.showerror(
             "Error al generar colores",
             "No se pudo obtener colores desde la API. Verifica internet o la API Key."
         ))

         self.estado_luces.set(False)
         self._mqtt_publish(TOPIC_NEOPIXEL, "255,0,0")

         def apagar_aviso():
            try:
                self._mqtt_publish(TOPIC_NEOPIXEL, "0,0,0")
            except:
                pass

         threading.Timer(2.0, apagar_aviso).start()



    def _slider_changed(self, _):
        # Slider del stepper (noria)
        val = self.velocidad.get()
        self.label_vel.config(text=f"Velocidad actual: {val}%")

        try:
            if self._vel_debounce_id:
                self.root.after_cancel(self._vel_debounce_id)
        except Exception:
            pass

        def enviar():
            if self._vel_last_sent == val:
                return
            self._vel_last_sent = val
            print(f"🎚 Usuario cambió velocidad stepper -> {val}% (publicando...)")
            self._mqtt_publish(TOPIC_STEPPER_SPEED, str(val))

        self._vel_debounce_id = self.root.after(200, enviar)

    def _dc_slider_changed(self, _):
     val = self.dc_speed.get()
     self.label_dc.config(text=f"DC: {val}%")
 
     try:
         if self._dc_debounce_id:
             self.root.after_cancel(self._dc_debounce_id)
     except Exception:
         pass
 
     def enviar():
         publish_value = int(val)
 
         if self._dc_last_sent == publish_value:
             return
 
         self._dc_last_sent = publish_value
         print(f"🎚 Usuario cambió velocidad DC -> {publish_value}% (publicando...)")
 
         # Aquí ya NO se pregunta si el motor está on/off
         # Solo se publica un número simple, como ESP32 espera
         self._mqtt_publish(TOPIC_DC_SPEED, str(publish_value))
 
     self._dc_debounce_id = self.root.after(200, enviar)

 

    def actualizar_estado(self, topic, payload):
        try:
            if topic == TOPIC_ERROR or topic.endswith("/error"):
                print("🚨 Error desde ESP32:", payload)
                messagebox.showerror("Error ESP32", payload)
                return

            if TOPIC_STATUS in topic or topic.endswith("/status"):
                print("ℹ️ Estado ESP:", payload)

            if TOPIC_NEOPIXEL in topic or "neopixel" in topic:
                try:
                    parsed = json.loads(payload)
                    if isinstance(parsed, dict) and "colors" in parsed:
                        colores = parsed["colors"]
                        display = ", ".join([f"{c[0]},{c[1]},{c[2]}" for c in colores])
                        self.label_colores.config(text=f"Colores: {display}")
                    else:
                        self.label_colores.config(text=f"Colores: {parsed}")
                except Exception:
                    self.label_colores.config(text=f"Colores: {payload}")

            elif TOPIC_DC_SPEED in topic or "dc_speed" in topic:
                # Esperamos recibir JSON o número
                try:
                    parsed = json.loads(payload)
                    if isinstance(parsed, dict) and "speed" in parsed:
                        num = int(parsed.get("speed", 0))
                    else:
                        num = int(float(payload))
                    self.label_dc.config(text=f"DC: {num}%")
                    self.dc_speed.set(num)
                except Exception:
                    self.label_dc.config(text=f"DC: {payload}")

            elif TOPIC_STEPPER_SPEED in topic or "stepper_speed" in topic or "dc_speed" not in topic and "stepper" in topic:
                try:
                    num = int(payload)
                    self.label_vel.config(text=f"Velocidad actual: {num}%")
                    self.velocidad.set(num)
                    self._vel_last_sent = num
                except Exception:
                    self.label_vel.config(text=f"Velocidad actual: {payload}")

            elif TOPIC_SONG in topic or "play_song" in topic or "music" in topic or "musica" in topic:
                state = payload.strip().lower() in ("1", "on", "start", "true", "encendido")
                self.estado_musica.set(state)

            elif TOPIC_SERVO in topic or "servo" in topic:
                state = payload.strip().lower() in ("open", "abrir", "true", "1")
                self.estado_servo.set(state)

            elif TOPIC_DISTANCE in topic or "sensor" in topic:
                # Mostrar texto directamente en la UI
                self.label_sensor.config(text=f"Sensor: {payload}")

        except Exception as e:
            print("⚠️ Error actualizando estado:", e)

    def _send_chatbot_command(self):
        text = self.chat_entry.get().strip()
        if not text:
            messagebox.showinfo("Chatbot", "Escribe un comando para enviar al ESP.")
            return
        print("💬 Enviando comando chatbot al ESP:", text)
        self._mqtt_publish(TOPIC_CHATBOT, text)
        self.chat_entry.delete(0, tk.END)

    def _trace_update(self, which):
        if which == "motor":
            print(f"🔁 Estado UI motor -> {self.estado_motor.get()}")
        elif which == "luces":
            print(f"🔁 Estado UI luces -> {self.estado_luces.get()}")
        elif which == "musica":
            print(f"🔁 Estado UI musica -> {self.estado_musica.get()}")
        elif which == "servo":
            print(f"🔁 Estado UI servo -> {self.estado_servo.get()}")

    def _shutdown(self):
        print("⏹ Cerrando aplicación — iniciando shutdown...")
        def do_shutdown():
            try:
                if self.mqtt_client:
                    print("🔌 Deteniendo loop MQTT...")
                    try:
                        self.mqtt_client.loop_stop()
                    except Exception as e:
                        print("⚠️ Error al detener loop MQTT:", e)
                    print("🔌 Desconectando broker MQTT...")
                    try:
                        self.mqtt_client.disconnect()
                        print("✔ MQTT desconectado correctamente.")
                    except Exception as e:
                        print("⚠️ Error al desconectar MQTT:", e)
            except Exception as e:
                print("⚠️ Error durante shutdown:", e)
            self.root.after(50, self.root.destroy)
        threading.Thread(target=do_shutdown, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = InterfazNoria(root)
    root.mainloop()
