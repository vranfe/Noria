# noria_esp32.py  -- MicroPython (ESP32)
import network, time, ujson, urequests, _thread
from umqtt.simple import MQTTClient
from machine import Pin, PWM
import neopixel

# ======================================================================
#                         CONFIGURACIÓN GENERAL
# ======================================================================
WIFI_SSID = "MOVISTAR_3C14"
WIFI_PASS = "QhMHsCWs5Y5H4SPmy8Qd"

OPENROUTER_API_KEY = "sk-or-..."  
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GEMINI_MODEL = "google/gemini-2.5-flash"

MQTT_SERVER = "broker.hivemq.com"
MQTT_PORT = 1883

TOPIC_NEOPIXEL = b"esp32/neopixel"
TOPIC_DC = b"esp32/dc_speed"
TOPIC_STEPPER = b"esp32/stepper_delay"
TOPIC_SONG = b"esp32/play_song"
TOPIC_VOLUME = b"esp32/buzzer_volume"
TOPIC_CHATBOT = b"esp32/chatbot_command"
TOPIC_ERROR = b"esp32/error"

DEBUG = False

# ======================================================================
#                               HARDWARE
# ======================================================================
NP_PIN = 5
NUM_LEDS = 16
np = neopixel.NeoPixel(Pin(NP_PIN), NUM_LEDS)

# Motor DC
pwm_A = PWM(Pin(27), freq=1000)
pin_B = Pin(14, Pin.OUT)
pin_B.value(0)

# Motor Paso a Paso
M1 = Pin(32, Pin.OUT)
M2 = Pin(33, Pin.OUT)
M3 = Pin(25, Pin.OUT)
M4 = Pin(26, Pin.OUT)

SEQUENCE = [
    (1,0,0,0), (1,1,0,0), (0,1,0,0), (0,1,1,0),
    (0,0,1,0), (0,0,1,1), (0,0,0,1), (1,0,0,1)
]

# Buzzer
buzzer_pin = Pin(18)
buzzer = PWM(buzzer_pin, freq=440, duty=0)
global_volume = 512  # duty inicial

# Música
notes = {
    'C4':262, 'D4':294, 'E4':330, 'F4':349, 'G4':392,
    'A4':440, 'B4':494, 'C5':523, 'PAUSE':0
}

circus_song = [
    ('G4',150),('E4',150),('G4',150),('E4',150),
    ('G4',300),('C4',150),('D4',150),('E4',150),
    ('F4',300),('PAUSE',100)
]

# ======================================================================
#                           ESTADO COMPARTIDO
# ======================================================================
step_delay = 10
stepper_running = False
stepper_lock = _thread.allocate_lock()

# ======================================================================
#                           FUNCIONES HARDWARE
# ======================================================================
def set_color(r,g,b):
    for i in range(NUM_LEDS):
        np[i] = (r,g,b)
    np.write()

def motor_dc_speed(percent):
    p = max(0, min(100, int(percent)))
    pwm_A.duty(int(p * 10.23))

def step_once():
    for a,b,c,d in SEQUENCE:
        M1.value(a)
        M2.value(b)
        M3.value(c)
        M4.value(d)
        time.sleep_ms(1)

def play_circus_thread():
    """Corre en segundo hilo para no bloquear."""
    for note, dur in circus_song:
        freq = notes.get(note, 0)
        if freq == 0:
            buzzer.duty(0)
        else:
            buzzer.freq(freq)
            buzzer.duty(global_volume)
        time.sleep_ms(dur)
    buzzer.duty(0)

def play_circus():
    _thread.start_new_thread(play_circus_thread, ())

# ======================================================================
#                             INTELIGENCIA ARTIFICIAL
# ======================================================================
SYSTEM_PROMPT = 'Responde solo JSON en formato {"actions":[...]}'

def call_ai(prompt):
    try:
        headers = {
            'Authorization': 'Bearer ' + OPENROUTER_API_KEY,
            'Content-Type': 'application/json'
        }
        data = {
            'model': GEMINI_MODEL,
            'messages': [
                {'role':'system','content':SYSTEM_PROMPT},
                {'role':'user','content':prompt}
            ]
        }
        resp = urequests.post(OPENROUTER_URL, headers=headers, data=ujson.dumps(data))

        if resp.status_code != 200:
            try: client.publish(TOPIC_ERROR, b"Error API")
            except: pass
            resp.close()
            return None

        j = resp.json()
        resp.close()
        content = j['choices'][0]['message']['content']
        content = content.replace("```json","").replace("```","").strip()
        return content

    except Exception:
        try: client.publish(TOPIC_ERROR, "Conexion API falló")
        except: pass
        return None

def execute_actions(json_text):
    try:
        d = ujson.loads(json_text)
        actions = d.get('actions', [])

        for a in actions:
            act = a.get('action')
            val = a.get('value')

            if act == 'set_speed':
                motor_dc_speed(int(val))

            elif act == 'set_color':
                r,g,b = [int(x) for x in val.split(',')]
                set_color(r,g,b)

            elif act == 'set_stepper_delay':
                global step_delay, stepper_running
                with stepper_lock:
                    step_delay = max(1, int(val))
                    stepper_running = True

            elif act == 'play_song':
                play_circus()

            elif act == 'set_volume':
                global global_volume
                p = max(0, min(100, int(val)))
                global_volume = int(p * 10.23)

    except Exception:
        try: client.publish(TOPIC_ERROR, b"JSON IA invalido")
        except: pass

# ======================================================================
#                           HILO STEPPER
# ======================================================================
def stepper_thread():
    global stepper_running, step_delay
    while True:
        if not stepper_running:
            time.sleep_ms(30)
            continue

        with stepper_lock:
            sd = step_delay

        for a,b,c,d in SEQUENCE:
            if not stepper_running:
                break
            M1.value(a)
            M2.value(b)
            M3.value(c)
            M4.value(d)
            time.sleep_ms(sd)

_thread.start_new_thread(stepper_thread, ())

# ======================================================================
#                           MQTT CALLBACK
# ======================================================================
def mqtt_callback(topic, msg):
    global stepper_running, step_delay, global_volume

    try:
        s = msg.decode()
    except:
        s = str(msg)

    if topic == TOPIC_NEOPIXEL:
        try:
            r,g,b = [int(x) for x in s.split(',')]
            set_color(r,g,b)
        except:
            client.publish(TOPIC_ERROR, b"Color invalido")

    elif topic == TOPIC_DC:
        try:
            motor_dc_speed(int(s))
        except:
            client.publish(TOPIC_ERROR, b"DC invalido")

    elif topic == TOPIC_STEPPER:
        try:
            v = int(s)
            with stepper_lock:
                if v >= 500:
                    stepper_running = False
                else:
                    step_delay = max(1, v)
                    stepper_running = True
        except:
            client.publish(TOPIC_ERROR, b"Stepper invalido")

    elif topic == TOPIC_SONG:
        if s == "start":
            play_circus()

    elif topic == TOPIC_VOLUME:
        try:
            p = max(0, min(100, int(s)))
            global_volume = int(p * 10.23)
        except:
            client.publish(TOPIC_ERROR, b"Volume invalido")

    elif topic == TOPIC_CHATBOT:
        ai_resp = call_ai(s)
        if ai_resp:
            execute_actions(ai_resp)
        else:
            client.publish(TOPIC_ERROR, b"No IA")

# ======================================================================
#                        WIFI Y MQTT
# ======================================================================
def wifi_connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASS)
        while not wlan.isconnected():
            time.sleep(1)

def mqtt_connect():
    global client
    client = MQTTClient("esp32_full_noria", MQTT_SERVER, MQTT_PORT)
    client.set_callback(mqtt_callback)
    client.connect()

    client.subscribe(TOPIC_NEOPIXEL)
    client.subscribe(TOPIC_DC)
    client.subscribe(TOPIC_STEPPER)
    client.subsc
