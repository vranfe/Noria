import re
import requests
from config import AppConfig, app_config


class GeminiColorAPI:
    """
    Genera paletas RGB usando OpenRouter (modelo Google Gemini Flash 2.5)
    Devuelve SIEMPRE un diccionario:
    {
        "colors": [
            {"r":123, "g":50, "b":200},
            ...
        ]
    }
    """

    def __init__(self, config: AppConfig = app_config):

        self.api_key = config.gemini.GEMINI_API_KEY
        self.model = "google/gemini-2.5-flash"
        self.temperature = config.gemini.TEMPERATURE

        self.url = "https://openrouter.ai/api/v1/chat/completions"

        print(f"🤖 OpenRouter inicializado con modelo: {self.model}")

    # -------------------------------------------------------------
    def _parse_color(self, text):
        """Convierte cualquier formato a (r,g,b)"""

        if isinstance(text, (list, tuple)) and len(text) == 3:
            return tuple(int(v) for v in text)

        if isinstance(text, dict) and all(k in text for k in ("r", "g", "b")):
            return (int(text["r"]), int(text["g"]), int(text["b"]))

        if isinstance(text, str):
            cleaned = text.lower().strip()
            cleaned = cleaned.replace("rgb", "").replace("(", "").replace(")", "")
            nums = re.findall(r"\d{1,3}", cleaned)
            if len(nums) == 3:
                return tuple(int(n) for n in nums)

        return None

    # -------------------------------------------------------------
    def get_colors_from_prompt(self, prompt, n_colors=5):

        prompt_text = f"""
Genera exactamente {n_colors} colores en formato RGB.
Salida SOLO líneas con: R,G,B
Sin texto adicional.
Tema: "{prompt}"
"""

        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": 128,     # evitar error 402
            "messages": [
                {"role": "user", "content": prompt_text}
            ]
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost",
            "X-Title": "Noria",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(self.url, json=payload, headers=headers)

            print("🔎 Respuesta OpenRouter RAW:", response.text)

            data = response.json()

            # --------------------------------------------------
            # EXTRAER TEXTO SEGÚN FORMATO DE OPENROUTER
            # --------------------------------------------------
            if "choices" in data:
                text = data["choices"][0]["message"]["content"]

            elif "response" in data and isinstance(data["response"], str):
                text = data["response"]

            elif "error" in data:
                print("❌ Error OpenRouter:", data["error"].get("message"))
                return {"colors": [{"r": 255, "g": 0, "b": 0}] * n_colors}

            else:
                print("⚠️ Respuesta sin campos choices/response")
                return {"colors": [{"r": 255, "g": 0, "b": 0}] * n_colors}

            # --------------------------------------------------
            # PROCESAR TEXTO EN FORMATO R,G,B
            # --------------------------------------------------
            text = text.strip()
            resultado = []

            for line in text.splitlines():
                color = self._parse_color(line)
                if color:
                    resultado.append(color)

            # Si vienen menos de los necesarios → completar
            while len(resultado) < n_colors:
                resultado.append((255, 0, 0))

            # --------------------------------------------------
            # 🔥 FORMATO COMPATIBLE CON interfaz.py
            # --------------------------------------------------
            colors_json = [{"r": r, "g": g, "b": b} for (r, g, b) in resultado]

            return {"colors": colors_json}

        except Exception as e:
            print("❌ Error en OpenRouter:", e)
            fallback = [{"r": 255, "g": 0, "b": 0}] * n_colors
            return {"colors": fallback}




