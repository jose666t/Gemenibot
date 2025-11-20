import os
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import re

load_dotenv()

app = Flask(__name__)

# Config desde env
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "miverificacion")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# URLs
WHATSAPP_API_URL = "https://graph.facebook.com/v13.0"
GEMINI_TEXT_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
GEMINI_IMAGE_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateImage"

# -------------------------
# Heurística simple para detectar peticiones de imagen
# -------------------------
IMAGE_KEYWORDS = [
    "imagen", "imagen de", "genera una imagen", "genera imagen", "foto", "fotografía",
    "dibujar", "dibujo", "ilustración", "haz una imagen", "quiero una imagen",
    "crea una imagen", "crear imagen", "pintar", "pintura", "render", "illustration",
    "draw", "generate image", "make an image", "picture of", "photo of"
]

def is_image_request(text: str) -> bool:
    if not text:
        return False
    txt = text.lower()
    # Coincidencia simple de palabras/frases
    for kw in IMAGE_KEYWORDS:
        if kw in txt:
            return True
    # Si el texto contiene "describe" o "explica" es texto, no imagen
    if re.search(r"\b(explica|describe|qué es|quién es|cómo|por qué)\b", txt):
        return False
    # Si hay muchos sustantivos cortos podríamos asumir texto — heurística simple.
    return False

# -------------------------
# Webhook (verificación GET)
# -------------------------
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403

# -------------------------
# Webhook (recepción de mensajes)
# -------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    # Validar estructura básica
    try:
        entries = data.get("entry", [])
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                messages = value.get("messages", [])
                if not messages:
                    continue
                message = messages[0]
                from_number = message.get("from")
                text_body = message.get("text", {}).get("body", "")
                # Decide imagen o texto
                if is_image_request(text_body):
                    prompt = text_body
                    image_url = generate_image(prompt)
                    if image_url:
                        send_image(from_number, image_url)
                    else:
                        send_text(from_number, "Lo siento, no pude generar la imagen ahora.")
                else:
                    # Generar respuesta de texto
                    reply = generate_text(text_body)
                    if reply:
                        send_text(from_number, reply)
                    else:
                        send_text(from_number, "Error al generar respuesta.")
    except Exception as e:
        app.logger.error("Webhook processing error: %s", e)
    return jsonify(status="received"), 200

# -------------------------
# Envíos a WhatsApp Cloud API
# -------------------------
def send_text(to: str, message: str):
    url = f"{WHATSAPP_API_URL}/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message}
    }
    resp = requests.post(url, headers=headers, json=payload)
    app.logger.info("send_text status=%s body=%s", resp.status_code, resp.text)
    return resp

def send_image(to: str, image_url: str):
    url = f"{WHATSAPP_API_URL}/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "image",
        "image": {"link": image_url}
    }
    resp = requests.post(url, headers=headers, json=payload)
    app.logger.info("send_image status=%s body=%s", resp.status_code, resp.text)
    return resp

# -------------------------
# Gemini: generar texto
# -------------------------
def generate_text(prompt: str) -> str:
    try:
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        params = {"key": GEMINI_API_KEY}
        resp = requests.post(GEMINI_TEXT_URL, params=params, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        # Navegar por la estructura (puede variar según versión)
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        app.logger.error("generate_text error: %s", e)
        return None

# -------------------------
# Gemini: generar imagen
# -------------------------
def generate_image(prompt: str) -> str:
    try:
        payload = {"prompt": {"text": prompt}}
        params = {"key": GEMINI_API_KEY}
        resp = requests.post(GEMINI_IMAGE_URL, params=params, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        # Estructura: data["generatedImages"][0]["url"]
        img_url = data.get("generatedImages", [{}])[0].get("url")
        return img_url
    except Exception as e:
        app.logger.error("generate_image error: %s", e)
        return None

# -------------------------
# Ruta raiz para comprobar servicio (Render)
# -------------------------
@app.route("/", methods=["GET"])
def home():
    return "Bot WhatsApp + Gemini activo ✅", 200

# Ejecutar local (no usado por gunicorn en Render)
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
