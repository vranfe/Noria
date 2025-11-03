import tkinter as tk
from PIL import Image, ImageTk
import paho.mqtt.client as mqtt
import threading
import json
import time

# Importar configuración y la función de ChatGPT
from config import MQTT_BROKER as BROKER, MQTT_PORT as PORT, TOPIC_CONTROL, TOPIC_ESTADO, OPENAI_API_KEY
from chatgpt_api import generar_colores_json

class InterfazNoria:
    def __init__(self, root):
        self.root = root
        self.root.minsize(700, 500)
        self.root.resizable(True, True)
        self.root.title("Control de la Noria 🎡")
        self.root.geometry("800x600")
        self.root.configure(bg="#FFE5B4")

        self.fuente = ("Comic Sans MS", 13, "bold")

        # --- Colores de la paleta ---
        self.COLOR_BASE_APAGADO = "#FFA726"
        self.COLOR_BASE_ENCENDIDO = "#FFB980"
        self.COLOR_TEXTO_APAGADO = "#BF360C"
        self.COLOR_TEXTO_ENCENDIDO = "#E65100"

        # --- MQTT: cliente dentro de la interfaz ---
        self._setup_mqtt()

        # --- Pantalla de bienvenida ---
        self.frame_bienvenida = tk.Frame(self.root, bg="#FFE5B4")
        self.frame_bienvenida.pack(expand=True, fill="both")

        tk.Label(
            self.frame_bienvenida,
            text="🎡 Bienvenido al Control de la Noria 🎡",
            font=("Comic Sans MS", 22, "bold"),
            fg="#FF6F00", bg="#FFE5B4"
        ).pack(pady=80)

        # Logo
        try:
            img = Image.open("assets/logo.png").resize((200, 200))
            self.logo = ImageTk.PhotoImage(img)
            tk.Label(self.frame_bienvenida, image=self.logo, bg="#FFE5B4").pack(pady=20)
        except:
            tk.Label(self.frame_bienvenida, text="(Logo no encontrado)", bg="#FFE5B4", fg="#FF6F00").pack(pady=20)

        tk.Button(
            self.frame_bienvenida, text="Entrar al Panel 🚀",
            command=self.abrir_panel, font=self.fuente,
            bg="#FF854D", fg="white", activebackground="#FF9800",
            relief="flat", width=20, height=2
        ).pack(pady=40)

    # ---------------- MQTT setup ----------------
    def _setup_mqtt(self):
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message_internal

        try:
            self.mqtt_client.connect(BROKER, PORT, 60)
            self.mqtt_client.loop_start()
            print("🔗 Intentando conexión con el broker MQTT...")
        except Exception as e:
            print("⚠️ No se pudo conectar al broker MQTT:", e)

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        print("🔗 Conectado al broker MQTT con código:", rc)
        try:
            client.subscribe(f"{TOPIC_ESTADO}/#")
            print(f"📡 Suscrito a {TOPIC_ESTADO}/# para recibir estados.")
        except Exception as e:
            print("⚠️ Error al suscribirse:", e)

    def _on_mqtt_message_internal(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode(errors="replace")
        print(f"📩 Recibido -> {topic}: {payload}")
        self.root.after(0, lambda: self.actualizar_estado(topic, payload))

    def _mqtt_publish(self, topic, payload):
        try:
            if isinstance(payload, dict):
                payload = json.dumps(payload)
            self.mqtt_client.publish(topic, payload)
            print(f"📤 Publicado {topic} -> {payload}")
        except Exception as e:
            print("⚠️ Error al publicar MQTT:", e)

    # ---------------- UI ----------------
    def abrir_panel(self):
        self.frame_bienvenida.destroy()
        self.panel_control()

    def panel_control(self):
        panel = tk.Frame(self.root, bg="#FFE5B4")
        panel.pack(expand=True, fill="both")

        tk.Label(
            panel, text="Panel de Control de la Noria",
            font=("Comic Sans MS", 20, "bold"), bg="#FFE5B4", fg="#E65100"
        ).pack(pady=20)

        self.icons = {}
        try:
            self.icons["motor"] = ImageTk.PhotoImage(Image.open("assets/motor.png").resize((35, 35)))
            self.icons["luces"] = ImageTk.PhotoImage(Image.open("assets/luces.png").resize((35, 35)))
            self.icons["musica"] = ImageTk.PhotoImage(Image.open("assets/musica.png").resize((35, 35)))
        except:
            print("⚠️ No se encontraron íconos en la carpeta assets.")

        # Variables de estado (bidireccionales)
        self.estado_motor = tk.BooleanVar(value=False)
        self.estado_luces = tk.BooleanVar(value=False)
        self.estado_musica = tk.BooleanVar(value=False)

        # Botones de control
        self.boton_motor = self.crear_boton(panel, "Iniciar Noria", self.icons.get("motor"), self.COLOR_BASE_APAGADO, self.estado_motor)
        self.boton_luces = self.crear_boton(panel, "Luces", self.icons.get("luces"), self.COLOR_BASE_APAGADO, self.estado_luces)
        self.boton_musica = self.crear_boton(panel, "Música", self.icons.get("musica"), self.COLOR_BASE_APAGADO, self.estado_musica)

        # Control de velocidad
        self.velocidad = tk.IntVar(value=50)
        tk.Label(panel, text="Velocidad de la Noria", font=self.fuente, bg="#FFE5B4", fg="#BF360C").pack(pady=10)
        tk.Scale(panel, from_=0, to=100, orient="horizontal", variable=self.velocidad,
                 command=self.cambiar_velocidad, length=400,
                 bg="#FFE5B4", fg="#BF360C", troughcolor="#FFD180").pack()
        self.label_vel = tk.Label(panel, text="Velocidad actual: 50%", font=self.fuente, bg="#FFE5B4", fg="#BF360C")
        self.label_vel.pack(pady=5)

        # Colores de ChatGPT
        self.label_colores = tk.Label(panel, text="Colores: -", font=("Comic Sans MS", 11), bg="#FFE5B4")
        self.label_colores.pack(pady=5)

        tk.Button(
            panel, text="Salir 🚪", command=self._shutdown,
            font=self.fuente, bg="#E64A19", fg="white", activebackground="#BF360C",
            relief="raised", width=12, height=2
        ).pack(pady=40)

    def crear_boton(self, parent, texto, icono, color_base, variable):
        frame = tk.Frame(parent, bg="#FFE5B4")
        frame.pack(pady=10, expand=True, anchor="center")

        boton = tk.Button(
            frame, text=texto, image=icono, compound="left",
            bg=color_base, fg="white", font=self.fuente,
            width=180, height=50, relief="flat", bd=0,
            activebackground=color_base
        )
        boton.pack(side="left", padx=10)

        label_estado = tk.Label(
            frame,
            text="Apagado",
            font=self.fuente,
            bg="#FFE5B4",
            fg=self.COLOR_TEXTO_APAGADO,
            width=9,
            anchor="w"
        )
        label_estado.pack(side="left", padx=10)

        boton.bind("<Button-1>", lambda e: self.toggle(boton, color_base, variable, label_estado, texto.lower()))
        return boton

    def toggle(self, boton, color_base, variable, label_estado, accion):
        estado = not variable.get()
        variable.set(estado)

        nuevo_color_boton = self.COLOR_BASE_ENCENDIDO if estado else color_base
        texto_label = "Encendido" if estado else "Apagado"
        color_label_texto = self.COLOR_TEXTO_ENCENDIDO if estado else self.COLOR_TEXTO_APAGADO

        boton.config(bg=nuevo_color_boton, activebackground=nuevo_color_boton)
        label_estado.config(text=texto_label, fg=color_label_texto)

        topic = f"noria/control/{accion}"

        if accion == "luces" and estado:
            label_estado.config(text="Conectando...", fg=self.COLOR_TEXTO_APAGADO)
            def worker():
                data = generar_colores_json()
                if data and "colors" in data:
                    self._mqtt_publish(topic, data)
                    colores_str = str(data["colors"])
                    self.root.after(0, lambda: label_estado.config(text="Encendido", fg=self.COLOR_TEXTO_ENCENDIDO))
                    self.root.after(0, lambda: self.label_colores.config(text=f"Colores: {colores_str}"))
                else:
                    self._mqtt_publish(topic, "1")
                    self.root.after(0, lambda: label_estado.config(text="Error", fg="red"))
            threading.Thread(target=worker, daemon=True).start()
            return

        valor = "1" if estado else "0"
        self._mqtt_publish(topic, valor)

    def cambiar_velocidad(self, _):
        val = self.velocidad.get()
        self.label_vel.config(text=f"Velocidad actual: {val}%")
        self._mqtt_publish("noria/control/velocidad", str(val))

    # ---------------- ACTUALIZACIÓN BIDIRECCIONAL ----------------
    def actualizar_estado(self, topic, valor):
        """Refleja en la interfaz lo que publica la Raspberry."""
        try:
            if "velocidad" in topic:
                self.label_vel.config(text=f"Velocidad actual: {valor}%")
                try:
                    self.velocidad.set(int(valor))
                except:
                    pass
            elif "motor" in topic:
                estado = valor.strip().lower() in ("1", "on", "encendido", "true")
                self.estado_motor.set(estado)
                print("⚙️ Motor ->", valor)
            elif "luces" in topic:
                try:
                    parsed = json.loads(valor)
                    colores = parsed.get("colors", parsed)
                    self.label_colores.config(text=f"Colores: {colores}")
                except:
                    self.label_colores.config(text=f"Colores: {valor}")
            elif "musica" in topic:
                estado = valor.strip().lower() in ("1", "on", "encendido", "true")
                self.estado_musica.set(estado)
        except Exception as e:
            print("⚠️ Error actualizando estado:", e)

    def _shutdown(self):
        try:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        except:
            pass
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = InterfazNoria(root)
    root.mainloop()
