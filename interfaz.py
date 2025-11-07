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
    """
    Clase principal que gestiona toda la aplicación.
    Contiene subclases para organizar la interfaz en pantallas.
    """

    def __init__(self, root):
        self.root = root
        self._configurar_ventana()
        self._definir_colores()
        self._setup_mqtt()

        # Crear pantalla inicial
        self.frame_bienvenida = self.Bienvenida(self)
        self.panel = None

    # ---------------- CONFIGURACIÓN GENERAL ----------------
    def _configurar_ventana(self):
        self.root.minsize(700, 500)
        self.root.resizable(True, True)
        self.root.title("Control de la Noria 🎡")
        self.root.geometry("800x600")
        self.root.configure(bg="#FFE5B4")
        self.fuente = ("Comic Sans MS", 13, "bold")

    def _definir_colores(self):
        self.COLOR_BASE_APAGADO = "#FFA726"
        self.COLOR_BASE_ENCENDIDO = "#FFB980"
        self.COLOR_TEXTO_APAGADO = "#BF360C"
        self.COLOR_TEXTO_ENCENDIDO = "#E65100"

    # ---------------- MQTT SETUP ----------------
    def _setup_mqtt(self):
        """Configuración del cliente MQTT (no modificada)."""
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
        """Callback al conectar al broker."""
        print("🔗 Conectado al broker MQTT con código:", rc)
        try:
            client.subscribe(f"{TOPIC_ESTADO}/#")
            print(f"📡 Suscrito a {TOPIC_ESTADO}/# para recibir estados.")
        except Exception as e:
            print("⚠️ Error al suscribirse:", e)

    def _on_mqtt_message_internal(self, client, userdata, msg):
        """Callback cuando se recibe un mensaje MQTT."""
        topic = msg.topic
        payload = msg.payload.decode(errors="replace")
        print(f"📩 Recibido -> {topic}: {payload}")
        self.root.after(0, lambda: self.actualizar_estado(topic, payload))

    def _mqtt_publish(self, topic, payload):
        """Publicar mensajes MQTT (sin cambios)."""
        try:
            if isinstance(payload, dict):
                payload = json.dumps(payload)
            self.mqtt_client.publish(topic, payload)
            print(f"📤 Publicado {topic} -> {payload}")
        except Exception as e:
            print("⚠️ Error al publicar MQTT:", e)

    # ---------------- SUBCLASE: PANTALLA DE BIENVENIDA ----------------
    class Bienvenida:
        """Pantalla de bienvenida de la interfaz."""

        def __init__(self, master):
            self.master = master
            self.frame = tk.Frame(master.root, bg="#FFE5B4")
            self.frame.pack(expand=True, fill="both")
            self._crear_componentes()

        def _crear_componentes(self):
            tk.Label(
                self.frame,
                text="🎡 Bienvenido al Control de la Noria 🎡",
                font=("Comic Sans MS", 22, "bold"),
                fg="#FF6F00", bg="#FFE5B4"
            ).pack(pady=80)

            # Logo
            try:
                img = Image.open("assets/logo.png").resize((200, 200))
                self.logo = ImageTk.PhotoImage(img)
                tk.Label(self.frame, image=self.logo, bg="#FFE5B4").pack(pady=20)
            except:
                tk.Label(self.frame, text="(Logo no encontrado)", bg="#FFE5B4", fg="#FF6F00").pack(pady=20)

            tk.Button(
                self.frame, text="Entrar al Panel 🚀",
                command=self._abrir_panel, font=self.master.fuente,
                bg="#FF854D", fg="white", activebackground="#FF9800",
                relief="flat", width=20, height=2
            ).pack(pady=40)

        def _abrir_panel(self):
            """Destruye la pantalla de bienvenida y abre el panel."""
            self.frame.destroy()
            self.master.panel = self.master.PanelControl(self.master)

    # ---------------- SUBCLASE: PANEL DE CONTROL ----------------
    class PanelControl:
        """Pantalla principal del panel de control."""

        def __init__(self, master):
            self.master = master
            self.panel = tk.Frame(master.root, bg="#FFE5B4")
            self.panel.pack(expand=True, fill="both")
            self._crear_panel()

        def _crear_panel(self):
            tk.Label(
                self.panel, text="Panel de Control de la Noria",
                font=("Comic Sans MS", 20, "bold"), bg="#FFE5B4", fg="#E65100"
            ).pack(pady=20)

            # Íconos
            self.icons = {}
            try:
                self.icons["motor"] = ImageTk.PhotoImage(Image.open("assets/motor.png").resize((35, 35)))
                self.icons["luces"] = ImageTk.PhotoImage(Image.open("assets/luces.png").resize((35, 35)))
                self.icons["musica"] = ImageTk.PhotoImage(Image.open("assets/musica.png").resize((35, 35)))
            except:
                print("⚠️ No se encontraron íconos en la carpeta assets.")

            # Variables de estado
            self.estado_motor = tk.BooleanVar(value=False)
            self.estado_luces = tk.BooleanVar(value=False)
            self.estado_musica = tk.BooleanVar(value=False)

            # Botones (subclase)
            self.boton_motor = self.master.BotonControl(self, "Iniciar Noria", "motor", self.estado_motor)
            self.boton_luces = self.master.BotonControl(self, "Luces", "luces", self.estado_luces)
            self.boton_musica = self.master.BotonControl(self, "Música", "musica", self.estado_musica)

            # Control de velocidad
            self.velocidad = tk.IntVar(value=50)
            tk.Label(self.panel, text="Velocidad de la Noria", font=self.master.fuente,
                     bg="#FFE5B4", fg="#BF360C").pack(pady=10)
            tk.Scale(self.panel, from_=0, to=100, orient="horizontal", variable=self.velocidad,
                     command=self._cambiar_velocidad, length=400,
                     bg="#FFE5B4", fg="#BF360C", troughcolor="#FFD180").pack()
            self.label_vel = tk.Label(self.panel, text="Velocidad actual: 50%", font=self.master.fuente,
                                      bg="#FFE5B4", fg="#BF360C")
            self.label_vel.pack(pady=5)

            # Colores ChatGPT
            self.label_colores = tk.Label(self.panel, text="Colores: -",
                                          font=("Comic Sans MS", 11), bg="#FFE5B4")
            self.label_colores.pack(pady=5)

            # Botón salir
            tk.Button(
                self.panel, text="Salir 🚪", command=self.master._shutdown,
                font=self.master.fuente, bg="#E64A19", fg="white", activebackground="#BF360C",
                relief="raised", width=12, height=2
            ).pack(pady=40)

        def _cambiar_velocidad(self, _):
            val = self.velocidad.get()
            self.label_vel.config(text=f"Velocidad actual: {val}%")
            self.master._mqtt_publish("noria/control/velocidad", str(val))

    # ---------------- SUBCLASE: BOTONES DE CONTROL ----------------
    class BotonControl:
        """Crea los botones de control con estado dinámico."""

        def __init__(self, panel, texto, accion, variable):
            self.panel = panel
            self.master = panel.master
            self.texto = texto
            self.accion = accion
            self.variable = variable
            self._crear_boton()

        def _crear_boton(self):
            frame = tk.Frame(self.panel.panel, bg="#FFE5B4")
            frame.pack(pady=10, expand=True, anchor="center")

            icono = self.panel.icons.get(self.accion)
            self.boton = tk.Button(
                frame, text=self.texto, image=icono, compound="left",
                bg=self.master.COLOR_BASE_APAGADO, fg="white", font=self.master.fuente,
                width=180, height=50, relief="flat", bd=0,
                activebackground=self.master.COLOR_BASE_APAGADO
            )
            self.boton.pack(side="left", padx=10)

            self.label_estado = tk.Label(
                frame, text="Apagado", font=self.master.fuente,
                bg="#FFE5B4", fg=self.master.COLOR_TEXTO_APAGADO,
                width=9, anchor="w"
            )
            self.label_estado.pack(side="left", padx=10)

            self.boton.bind("<Button-1>", self._toggle)

        def _toggle(self, _):
            estado = not self.variable.get()
            self.variable.set(estado)

            nuevo_color = self.master.COLOR_BASE_ENCENDIDO if estado else self.master.COLOR_BASE_APAGADO
            texto_label = "Encendido" if estado else "Apagado"
            color_texto = self.master.COLOR_TEXTO_ENCENDIDO if estado else self.master.COLOR_TEXTO_APAGADO

            self.boton.config(bg=nuevo_color, activebackground=nuevo_color)
            self.label_estado.config(text=texto_label, fg=color_texto)

            topic = f"noria/control/{self.accion}"

            # Caso especial: luces con ChatGPT
            if self.accion == "luces" and estado:
                self.label_estado.config(text="Conectando...", fg=self.master.COLOR_TEXTO_APAGADO)

                def worker():
                    data = generar_colores_json()
                    if data and "colors" in data:
                        self.master._mqtt_publish(topic, data)
                        colores_str = str(data["colors"])
                        self.master.root.after(0, lambda: self.label_estado.config(
                            text="Encendido", fg=self.master.COLOR_TEXTO_ENCENDIDO))
                        self.master.root.after(0, lambda: self.panel.label_colores.config(
                            text=f"Colores: {colores_str}"))
                    else:
                        self.master._mqtt_publish(topic, "1")
                        self.master.root.after(0, lambda: self.label_estado.config(text="Error", fg="red"))

                threading.Thread(target=worker, daemon=True).start()
                return

            valor = "1" if estado else "0"
            self.master._mqtt_publish(topic, valor)

    # ---------------- ACTUALIZACIÓN DE ESTADO ----------------
    def actualizar_estado(self, topic, valor):
        """Refleja en la interfaz lo que publica la Raspberry."""
        try:
            if not self.panel:
                return

            if "velocidad" in topic:
                self.panel.label_vel.config(text=f"Velocidad actual: {valor}%")
                try:
                    self.panel.velocidad.set(int(valor))
                except:
                    pass
            elif "motor" in topic:
                estado = valor.strip().lower() in ("1", "on", "encendido", "true")
                self.panel.estado_motor.set(estado)
            elif "luces" in topic:
                try:
                    parsed = json.loads(valor)
                    colores = parsed.get("colors", parsed)
                    self.panel.label_colores.config(text=f"Colores: {colores}")
                except:
                    self.panel.label_colores.config(text=f"Colores: {valor}")
            elif "musica" in topic:
                estado = valor.strip().lower() in ("1", "on", "encendido", "true")
                self.panel.estado_musica.set(estado)
        except Exception as e:
            print("⚠️ Error actualizando estado:", e)

    # ---------------- FINALIZACIÓN ----------------
    def _shutdown(self):
        """Cerrar correctamente MQTT y la ventana."""
        try:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        except:
            pass
        self.root.destroy()


# ---------------- MAIN ----------------
if __name__ == "__main__":
    root = tk.Tk()
    app = InterfazNoria(root)
    root.mainloop()
