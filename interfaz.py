# interfaz.py
"""
Interfaz gráfica para la Noria (MQTT + ESP32).
- Botones superiores centrados (mismo estilo visual).
- Slider Velocidad + Slider Volumen (debounce).
- Mensajes reducidos: sólo se imprime cuando el usuario inicia una acción.
- Manejo de errores IA: revierte estado si falla.
"""

import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import paho.mqtt.client as mqtt
import threading
import json
import time

# Importar configuración orientada a objetos (tu config.py)
from config import AppConfig
config = AppConfig()

# ---------------- TOPICS ESP32 ----------------
TOPIC_NEOPIXEL = "esp32/neopixel"
TOPIC_DC_SPEED = "esp32/dc_speed"
TOPIC_STEPPER = "esp32/stepper_delay"
TOPIC_SONG = "esp32/play_song"
TOPIC_VOLUME = "esp32/buzzer_volume"
TOPIC_CHATBOT = "esp32/chatbot_command"
TOPIC_ERROR = "esp32/error"
TOPIC_STATUS = "esp32/status"

# Importa API de colores (debe existir ChatGPTColorAPI.get_theme)
from chatgpt_api import ChatGPTColorAPI
color_gen = ChatGPTColorAPI(api_key=config.openai.OPENAI_API_KEY)


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
        self._vol_debounce_id = None
        self._vol_last_sent = None

        # Estados
        self.estado_motor = tk.BooleanVar(value=False)
        self.estado_luces = tk.BooleanVar(value=False)
        self.estado_musica = tk.BooleanVar(value=False)

        # Traces para mantener UI sincrónica
        self.estado_motor.trace_add("write", lambda *a: self._trace_update("motor"))
        self.estado_luces.trace_add("write", lambda *a: self._trace_update("luces"))
        self.estado_musica.trace_add("write", lambda *a: self._trace_update("musica"))

        # Bienvenida
        self.frame_bienvenida = tk.Frame(self.root, bg="#FFE5B4")
        self.frame_bienvenida.pack(expand=True, fill="both")
        self._crear_bienvenida()

        # Panel se crea al entrar
        self.panel = None

    # ---------------- Config ventana & colores ----------------
    def _configurar_ventana(self):
        self.root.title("Control de la Noria 🎡")
        self.root.geometry("900x650")
        self.root.minsize(700, 500)
        self.root.resizable(True, True)
        self.root.configure(bg="#FFE5B4")
        self.fuente = ("Comic Sans MS", 13, "bold")

    def _definir_colores(self):
        self.COLOR_BASE_APAGADO = "#FFA726"
        self.COLOR_BASE_ENCENDIDO = "#FFB980"
        self.COLOR_TEXTO_APAGADO = "#BF360C"
        self.COLOR_TEXTO_ENCENDIDO = "#E65100"

    # ---------------- MQTT setup ----------------
    def _setup_mqtt(self):
        try:
            self.mqtt_client = mqtt.Client()
            # usuario/clave opcional
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
            client.subscribe("esp32/#")
            print("📡 Suscrito a esp32/#")
        except Exception as e:
            print("⚠️ Error suscribiendo a topics:", e)

    def _on_mqtt_message_internal(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode(errors="replace")
            # NO imprimimos cada mensaje para evitar spam
            self.root.after(0, lambda: self.actualizar_estado(topic, payload))
        except Exception as e:
            print("⚠️ Error en on_message:", e)

    def _mqtt_publish(self, topic, payload):
        """
        Publica y registra en consola (solo cuando acción proviene del usuario).
        """
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

            # Mensaje claro en consola cuando el usuario publica algo
            print(f"📤 PUBLICAR -> {topic}: {payload}")
            self.mqtt_client.publish(topic, str(payload))
            print("   ✔ Enviado")
        except Exception as e:
            print("❌ Error al publicar MQTT:", e)

    # ---------------- Bienvenida ----------------
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
        self.frame_bienvenida.destroy()
        self._crear_panel_control()

    # ---------------- Panel principal ----------------
    def _crear_panel_control(self):
        self.panel = tk.Frame(self.root, bg="#FFE5B4")
        self.panel.pack(expand=True, fill="both")

        tk.Label(
            self.panel, text="Panel de Control de la Noria",
            font=("Comic Sans MS", 20, "bold"), bg="#FFE5B4", fg="#E65100"
        ).pack(pady=12)

        # iconos
        self.icons = {}
        try:
            self.icons["motor"] = ImageTk.PhotoImage(Image.open("assets/motor.png").resize((35, 35)))
            self.icons["luces"] = ImageTk.PhotoImage(Image.open("assets/luces.png").resize((35, 35)))
            self.icons["musica"] = ImageTk.PhotoImage(Image.open("assets/musica.png").resize((35, 35)))
            self.icons["salir"] = ImageTk.PhotoImage(Image.open("assets/salir.png").resize((28, 28)))
        except Exception:
            pass

        # TOP: fila de botones centrada (nuevo contenedor)
        top_btns_frame = tk.Frame(self.panel, bg="#FFE5B4")
        top_btns_frame.pack(pady=8)
        self.top_btns_frame = top_btns_frame  # referencia para BotonControl

        # botones (ahora se crean dentro del frame superior para alinearlos centrados)
        self.boton_motor = self.BotonControl(self, "Iniciar Noria", "motor", self.estado_motor, parent_frame=top_btns_frame)
        self.boton_luces = self.BotonControl(self, "Luces", "luces", self.estado_luces, parent_frame=top_btns_frame)
        self.boton_musica = self.BotonControl(self, "Música", "musica", self.estado_musica, parent_frame=top_btns_frame)

        # slider velocidad
        self.velocidad = tk.IntVar(value=50)
        tk.Label(self.panel, text="Velocidad de la Noria", font=self.fuente, bg="#FFE5B4", fg="#BF360C").pack(pady=8)
        self.scale = tk.Scale(self.panel, from_=0, to=100, orient="horizontal",
                              variable=self.velocidad, command=self._slider_changed,
                              length=480, bg="#FFE5B4", fg="#BF360C", troughcolor="#FFD180")
        self.scale.pack()
        self.label_vel = tk.Label(self.panel, text="Velocidad actual: 50%", font=self.fuente, bg="#FFE5B4", fg="#BF360C")
        self.label_vel.pack(pady=6)

        # label colores
        self.label_colores = tk.Label(self.panel, text="Colores: -", font=("Comic Sans MS", 11), bg="#FFE5B4")
        self.label_colores.pack(pady=6)

        # ----- slider VOLUMEN (debajo de velocidad) -----
        self.volumen = tk.IntVar(value=50)
        tk.Label(self.panel, text="Volumen de la Música", font=self.fuente, bg="#FFE5B4", fg="#BF360C").pack(pady=(12, 6))
        self.scale_vol = tk.Scale(self.panel, from_=0, to=100, orient="horizontal",
                                  variable=self.volumen, command=self._vol_slider_changed,
                                  length=480, bg="#FFE5B4", fg="#BF360C", troughcolor="#FFD180")
        self.scale_vol.pack()
        self.label_vol = tk.Label(self.panel, text="Volumen actual: 50%", font=self.fuente, bg="#FFE5B4", fg="#BF360C")
        self.label_vol.pack(pady=6)

        # chatbot entry (envío directo al TOPIC_CHATBOT)
        chatbot_frame = tk.Frame(self.panel, bg="#FFE5B4")
        chatbot_frame.pack(pady=8)
        tk.Label(chatbot_frame, text="Comando Chatbot (envía al ESP):", bg="#FFE5B4").grid(row=0, column=0, sticky="w")
        self.chat_entry = tk.Entry(chatbot_frame, width=50)
        self.chat_entry.grid(row=1, column=0, padx=6, pady=6)
        tk.Button(chatbot_frame, text="Enviar comando IA", command=self._send_chatbot_command).grid(row=1, column=1, padx=6)

        # salir
        salir_img = self.icons.get("salir")
        tk.Button(self.panel, text="Salir 🚪", command=self._shutdown, font=self.fuente,
                  bg="#E64A19", fg="white", activebackground="#BF360C",
                  relief="raised", width=12, height=2, image=salir_img, compound="left").pack(pady=12)

    # ---------------- Slider velocidad (debounce) ----------------
    def _slider_changed(self, _):
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
            print(f"🎚 Usuario cambió velocidad -> {val}% (publicando...)")
            self._mqtt_publish(TOPIC_DC_SPEED, str(val))
            # map % a delay
            min_delay, max_delay = 2, 50
            delay = int(max_delay - (val / 100.0) * (max_delay - min_delay))
            delay = max(1, delay)
            self._mqtt_publish(TOPIC_STEPPER, str(delay))

        self._vel_debounce_id = self.root.after(200, enviar)

    # ---------------- Slider volumen (debounce) ----------------
    def _vol_slider_changed(self, _):
        val = self.volumen.get()
        self.label_vol.config(text=f"Volumen actual: {val}%")

        try:
            if self._vol_debounce_id:
                self.root.after_cancel(self._vol_debounce_id)
        except Exception:
            pass

        def enviar_vol():
            if self._vol_last_sent == val:
                return
            self._vol_last_sent = val
            print(f"🔊 Usuario cambió volumen -> {val}% (publicando...)")
            # publicar TOPIC_VOLUME con porcentaje (ESP mapeará a duty)
            self._mqtt_publish(TOPIC_VOLUME, str(val))

        self._vol_debounce_id = self.root.after(200, enviar_vol)

    # ---------------- BotonControl ----------------
    class BotonControl:
        def __init__(self, master_app, texto, tipo, variable_estado: tk.BooleanVar, parent_frame=None):
            self.app = master_app
            # si recibimos parent_frame lo usamos (para centrar los 3 botones superiores)
            self.parent_frame = parent_frame if parent_frame is not None else master_app.panel
            self.tipo = tipo
            self.texto = texto
            self.variable = variable_estado

            # contenedor: si está en top buttons frame, alineamos en fila
            self.frame = tk.Frame(self.parent_frame, bg="#FFE5B4")
            # Decide packing según si parent es el top_btns_frame
            if getattr(master_app, "top_btns_frame", None) is self.parent_frame:
                self.frame.pack(side="left", padx=8)
            else:
                self.frame.pack(pady=8, anchor="w")

            icon = master_app.icons.get(tipo)
            self.btn = tk.Button(self.frame, text=texto, image=icon, compound="left",
                                 bg=master_app.COLOR_BASE_APAGADO, fg="white",
                                 font=master_app.fuente, width=180, height=48,
                                 relief="flat", bd=0, activebackground=master_app.COLOR_BASE_APAGADO,
                                 command=self._on_click)
            self.btn.pack(side="left", padx=6)

            self.label_estado = tk.Label(self.frame, text="Apagado", font=master_app.fuente,
                                         bg="#FFE5B4", fg=master_app.COLOR_TEXTO_APAGADO, width=10, anchor="w")
            self.label_estado.pack(side="left", padx=8)

            # trace para sincronizar UI si la var cambia desde fuera
            self.variable.trace_add("write", lambda *a: self._update_ui_state())
            self._update_ui_state()

        def _update_ui_state(self):
            estado = self.variable.get()
            if estado:
                self.btn.config(bg=self.app.COLOR_BASE_ENCENDIDO, activebackground=self.app.COLOR_BASE_ENCENDIDO)
                self.label_estado.config(text="Encendido", fg=self.app.COLOR_TEXTO_ENCENDIDO)
            else:
                self.btn.config(bg=self.app.COLOR_BASE_APAGADO, activebackground=self.app.COLOR_BASE_APAGADO)
                self.label_estado.config(text="Apagado", fg=self.app.COLOR_TEXTO_APAGADO)

        def _on_click(self):
            nuevo = not self.variable.get()
            self.variable.set(nuevo)
            print(f"🖱 Botón '{self.tipo}' presionado — nuevo estado: {nuevo}")

            if self.tipo == "motor":
                if nuevo:
                    val = self.app.velocidad.get()
                    min_d, max_d = 2, 50
                    delay = int(max_d - (val / 100.0) * (max_d - min_d))
                    delay = max(1, delay)
                    print(f"⚙️ Publicando inicio motor (delay={delay})")
                    self.app._mqtt_publish(TOPIC_STEPPER, str(delay))
                else:
                    print("🛑 Publicando detener motor")
                    self.app._mqtt_publish(TOPIC_STEPPER, "1000")

            elif self.tipo == "luces":
                if nuevo:
                    print("✨ Solicitando colores IA...")
                    self.label_estado.config(text="Conectando...", fg=self.app.COLOR_TEXTO_APAGADO)
                    threading.Thread(target=self._worker_luces, daemon=True).start()
                else:
                    print("🌑 Publicando apagar luces")
                    self.app._mqtt_publish(TOPIC_NEOPIXEL, "0,0,0")

            elif self.tipo == "musica":
                if nuevo:
                    vol = self.app.volumen.get() if hasattr(self.app, "volumen") else 50
                    print(f"🎵 Publicando volumen actual {vol}% y luego iniciar música")
                    self.app._mqtt_publish(TOPIC_VOLUME, str(vol))
                    self.app._mqtt_publish(TOPIC_SONG, "start")
                else:
                    print("🔇 Publicando silenciar (volume=0)")
                    self.app._mqtt_publish(TOPIC_VOLUME, "0")

        def _worker_luces(self):
            try:
                colors = color_gen.get_theme("Ilumina la noria con colores vibrantes", n_colors=3)

                if not colors or not isinstance(colors, list) or len(colors) == 0:
                    raise ValueError("Respuesta inválida de API")

                trip = colors[0]
                if not (isinstance(trip, (list, tuple)) and len(trip) >= 3):
                    raise ValueError("Formato de color inesperado")

                payload = f"{int(trip[0])},{int(trip[1])},{int(trip[2])}"
                print(f"🌈 Colores generados -> {payload} (publicando...)")
                self.app._mqtt_publish(TOPIC_NEOPIXEL, payload)

                colores_str = ", ".join([f"{c[0]},{c[1]},{c[2]}" for c in colors])
                self.app.root.after(0, lambda: self.app.label_colores.config(text=f"Colores: {colores_str}"))
                # asegurar que UI indica Encendido (var ya True)
                self.app.root.after(0, lambda: self.variable.set(True))

            except Exception as e:
                print("❌ Error ChatGPT (luces):", e)
                self.app.root.after(0, lambda: messagebox.showerror(
                    "Error al generar colores",
                    "No se pudo obtener colores desde la API.\nVerifica internet o la API Key."
                ))
                # revertir estado y encender aviso rojo por 2s
                self.variable.set(False)
                self.app._mqtt_publish(TOPIC_NEOPIXEL, "255,0,0")
                def apagar_aviso():
                    try:
                        self.app._mqtt_publish(TOPIC_NEOPIXEL, "0,0,0")
                    except:
                        pass
                threading.Timer(2.0, apagar_aviso).start()

    # ---------------- Actualizar estado desde ESP ----------------
    def actualizar_estado(self, topic, payload):
        try:
            if topic == TOPIC_ERROR or topic.endswith("/error"):
                print("🚨 Error desde ESP32:", payload)
                messagebox.showerror("Error ESP32", payload)
                return

            if TOPIC_STATUS in topic or topic.endswith("/status"):
                print("ℹ️ Estado ESP:", payload)

            if "neopixel" in topic:
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

            elif "dc_speed" in topic:
                try:
                    num = int(payload)
                    self.label_vel.config(text=f"Velocidad actual: {num}%")
                    self.velocidad.set(num)
                    self._vel_last_sent = num
                except Exception:
                    self.label_vel.config(text=f"Velocidad actual: {payload}")

            elif "buzzer" in topic or "play_song" in topic or "music" in topic or "musica" in topic:
                state = payload.strip().lower() in ("1", "on", "start", "true", "encendido")
                self.estado_musica.set(state)

            elif "buzzer_volume" in topic or "buzzer/volume" in topic or TOPIC_VOLUME in topic:
                try:
                    num = int(payload)
                    self.label_vol.config(text=f"Volumen actual: {num}%")
                    self.volumen.set(num)
                    self._vol_last_sent = num
                except Exception:
                    self.label_vol.config(text=f"Volumen actual: {payload}")

        except Exception as e:
            print("⚠️ Error actualizando estado:", e)

    # ---------------- Enviar comando Chatbot desde entrada ----------------
    def _send_chatbot_command(self):
        text = self.chat_entry.get().strip()
        if not text:
            messagebox.showinfo("Chatbot", "Escribe un comando para enviar al ESP.")
            return
        print("💬 Enviando comando chatbot al ESP:", text)
        self._mqtt_publish(TOPIC_CHATBOT, text)
        self.chat_entry.delete(0, tk.END)

    # ---------------- Trace (cuando cambia una BooleanVar) ----------------
    def _trace_update(self, which):
        if which == "motor":
            print(f"🔁 Estado UI motor -> {self.estado_motor.get()}")
        elif which == "luces":
            print(f"🔁 Estado UI luces -> {self.estado_luces.get()}")
        elif which == "musica":
            print(f"🔁 Estado UI musica -> {self.estado_musica.get()}")

    # ---------------- Shutdown seguro ----------------
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


# ---------------- main ----------------
if __name__ == "__main__":
    root = tk.Tk()
    app = InterfazNoria(root)
    root.mainloop()

