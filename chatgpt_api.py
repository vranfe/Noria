import os
import json
from openai import OpenAI


class ColorGenerator:
    """
    Clase para generar combinaciones de colores usando el modelo de OpenAI.
    Devuelve 3 colores vibrantes en formato JSON: {"colors":[[r,g,b],[r,g,b],[r,g,b]]}
    """

    def __init__(self, api_key=None, model="gpt-3.5-turbo"):
        """
        Inicializa el cliente de OpenAI.
        Si no se pasa una clave, intenta obtenerla de la variable de entorno OPENAI_API_KEY.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "TU_API_KEY_AQUI")
        self.client = OpenAI(api_key=self.api_key)
        self.model = model

    def generar_colores_json(self):
        """
        Envía un prompt al modelo para generar 3 colores en formato JSON.
        Retorna un diccionario o None en caso de error.
        """
        prompt = (
            "Genera 3 colores vibrantes para iluminar una noria de feria y "
            "devuélvelos exclusivamente en formato JSON así: "
            "{\"colors\":[[r,g,b],[r,g,b],[r,g,b]]} "
            "con valores enteros de 0 a 255. "
            "No agregues texto adicional ni explicaciones."
        )

        try:
            # ✅ Solicitud al modelo
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.8
            )

            text = response.choices[0].message.content.strip()

            # 🔍 Extraer solo el bloque JSON válido
            start = text.find("{")
            end = text.rfind("}")
            json_text = text[start:end + 1] if start != -1 and end != -1 else text

            # 📦 Convertir a dict
            data = json.loads(json_text)
            return data

        except Exception as e:
            print("❌ Error al generar colores con ChatGPT:", e)
            return None



