import os
import json
from openai import OpenAI

# Tu clave API (puede venir de config.py o directamente acá)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "TU_API_KEY_AQUI")

client = OpenAI(api_key=OPENAI_API_KEY)

def generar_colores_json():
    """
    Pide a OpenAI 3 colores en formato JSON: {"colors":[[r,g,b],[r,g,b],[r,g,b]]}
    Devuelve dict o None.
    """
    prompt = (
        "Genera 3 colores vibrantes para iluminar una noria de feria y "
        "devuélvelos exclusivamente en JSON así: "
        "{\"colors\":[[r,g,b],[r,g,b],[r,g,b]]} con r,g,b enteros 0-255. "
        "No agregues texto adicional."
    )

    try:
        # ✅ Nueva sintaxis con openai>=1.0.0
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.8
        )

        text = resp.choices[0].message.content.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_text = text[start:end + 1]
        else:
            json_text = text

        data = json.loads(json_text)
        return data

    except Exception as e:
        print("❌ Error al consultar ChatGPT:", e)
        return None
