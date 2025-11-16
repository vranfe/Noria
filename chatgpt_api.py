import json
import requests

class ChatGPTColorAPI:
    def __init__(self, api_key, model="gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self.url = "https://api.openai.com/v1/chat/completions"

    def get_colors_from_prompt(self, prompt):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Devuélveme colores en formato 'R,G,B'."},
                {"role": "user", "content": f"Convierte este texto en colores RGB: {prompt}"}
            ],
            "max_tokens": 50,
            "temperature": 0.3
        }

        try:
            response = requests.post(self.url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()

            raw_text = result["choices"][0]["message"]["content"]

            # Extraer líneas que tengan formato R,G,B
            colors = []
            for line in raw_text.splitlines():
                line = line.strip()
                if "," in line:
                    parts = line.split(",")
                    if len(parts) == 3:
                        try:
                            r = int(parts[0])
                            g = int(parts[1])
                            b = int(parts[2])

                            if 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255:
                                colors.append(f"{r},{g},{b}")
                        except:
                            pass

            if not colors:
                return ["255,0,0"]  # fallback: rojo

            return colors

        except Exception as e:
            print("Error llamando a ChatGPT:", e)
            return ["255,0,0"]  # fallback
