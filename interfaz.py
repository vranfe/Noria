import tkinter as tk
from PIL import Image, ImageTk

# import paho.mqtt.client as mqtt  MQTT 

"""
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_CONTROL = "noria/control/#"
TOPIC_ESTADO = "noria/estado/#"

def conectar_mqtt():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    return client

def on_connect(client, userdata, flags, rc):
    print("Conectado al broker con código:", rc)
    client.subscribe(TOPIC_ESTADO)

def on_message(client, userdata, msg):
    print(f"Mensaje recibido: {msg.topic} -> {msg.payload.decode()}")
"""

def enviar_comando(accion, valor=None):
    data = {"accion": accion, "valor": valor}
    print("Comando simulado:", data)


class InterfazNoria:
    def __init__(self, root):
        self.root = root
        self.root.minsize(700, 500)
        self.root.resizable(True, True)

        self.root.title("Control de la Noria 🎡")
        self.root.geometry("800x600")
        self.root.configure(bg="#FFE5B4")
        
        self.fuente = ("Comic Sans MS", 13, "bold")

        # --- Definimos los colores de tu paleta ---
        self.COLOR_BASE_APAGADO = "#FFA726" # Naranja base (Consistente)
        self.COLOR_BASE_ENCENDIDO = "#FFB980" # Naranja claro
        
        # Colores para el texto de estado
        self.COLOR_TEXTO_APAGADO = "#BF360C" # Naranja oscuro
        self.COLOR_TEXTO_ENCENDIDO = "#E65100" # Naranja brillante

        self.frame_bienvenida = tk.Frame(self.root, bg="#FFE5B4")
        self.frame_bienvenida.pack(expand=True, fill="both")

        tk.Label(
            self.frame_bienvenida, 
            text="🎡 Bienvenido al Control de la Noria 🎡",
            font=("Comic Sans MS", 22, "bold"),
            fg="#FF6F00", bg="#FFE5B4"
        ).pack(pady=80)

        # --- LOGO ---
        self.logo = None
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

        # Cargar iconos
        self.icons = {}
        try:
            self.icons["motor"] = ImageTk.PhotoImage(Image.open("assets/motor.png").resize((35, 35)))
            self.icons["luces"] = ImageTk.PhotoImage(Image.open("assets/luces.png").resize((35, 35)))
            self.icons["musica"] = ImageTk.PhotoImage(Image.open("assets/musica.png").resize((35, 35)))
            
        except:
            print("⚠️ No se encontraron algunos íconos en la carpeta assets.")

        self.estado_motor = tk.BooleanVar(value=False)
        self.estado_luces = tk.BooleanVar(value=False)
        self.estado_musica = tk.BooleanVar(value=False)

        # Botones (ahora con el color base unificado)
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

        
        
        #  BOTÓN SALIR 
        tk.Button(
        panel, text="Salir 🚪", command=self.root.destroy,
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
        
        # --- ETIQUETA DE ESTADO (CON LA CORRECCIÓN) ---
        label_estado = tk.Label(
            frame, 
            text="Apagado", 
            font=self.fuente,
            bg="#FFE5B4",
            fg=self.COLOR_TEXTO_APAGADO,
            width=9,          # <-- ANCHO FIJO (basado en "Encendido")
            anchor="w"        # <-- Alinea el texto a la izquierda (West)
        )
        label_estado.pack(side="left", padx=10)
        
        boton.bind("<Button-1>", lambda e: self.toggle(boton, color_base, variable, label_estado))
        return boton

    def toggle(self, boton, color_base, variable, label_estado):
        estado = not variable.get()
        variable.set(estado)
        
        if estado:
            nuevo_color_boton = self.COLOR_BASE_ENCENDIDO
            texto_label = "Encendido"
            color_label_texto = self.COLOR_TEXTO_ENCENDIDO
        else:
            nuevo_color_boton = color_base
            texto_label = "Apagado"
            color_label_texto = self.COLOR_TEXTO_APAGADO

        # Actualizar el botón
        boton.config(bg=nuevo_color_boton, activebackground=nuevo_color_boton)
        
        # Actualizar la etiqueta
        label_estado.config(text=texto_label, fg=color_label_texto)
        
        enviar_comando(boton.cget("text").lower(), "Encendido" if estado else "Apagado")

    def cambiar_velocidad(self, _):
        val = self.velocidad.get()
        self.label_vel.config(text=f"Velocidad actual: {val}%")
        enviar_comando("velocidad", val)

    
if __name__ == "__main__":
    root = tk.Tk()
    app = InterfazNoria(root)
    root.mainloop()

