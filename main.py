import os
from fastapi import FastAPI, Request, Query
from fastapi.responses import PlainTextResponse
import requests
from dotenv import load_dotenv
from bot import procesar_mensaje

load_dotenv()  # Carga las variables del archivo .env

app = FastAPI()

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

@app.get("/webhook")
async def verify_webhook(hub_mode: str = Query(None, alias="hub.mode"),
                         hub_challenge: str = Query(None, alias="hub.challenge"),
                         hub_verify_token: str = Query(None, alias="hub.verify_token")):
    if hub_verify_token == VERIFY_TOKEN:
        return PlainTextResponse(hub_challenge, status_code=200)
    return {"error": "Token inválido"}, 403

@app.post("/webhook")
async def receive_message(request: Request):
    body = await request.json()
    try:
        entry = body["entry"][0]["changes"][0]["value"]
        if "messages" in entry:
            message = entry["messages"][0]
            phone = message["from"]
            text = message["text"]["body"]
            # Procesamos el mensaje con nuestro bot dental
            response_text = procesar_mensaje(text)
            send_whatsapp_message(phone, response_text)
    except Exception as e:
        print("Error procesando mensaje:", e)
    return {"status": "ok"}

def send_whatsapp_message(to, text):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": text}
    }
    response = requests.post(url, json=data, headers=headers)
    print("WhatsApp response:", response.json())