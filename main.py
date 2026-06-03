import os
from fastapi import FastAPI, Request, Query
from fastapi.responses import PlainTextResponse
import requests
from dotenv import load_dotenv
from sqlalchemy import text

from database import SessionLocal
from models import Clinica
from bot import procesar_mensaje

# Cargar variables de entorno solo en local
if not os.getenv("RENDER"):
    load_dotenv()

app = FastAPI()

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

# -----------------------------------------------
# Endpoint de salud
# -----------------------------------------------
@app.get("/health")
def health_check():
    return {"status": "ok"}

# -----------------------------------------------
# Endpoint de diagnóstico de base de datos
# -----------------------------------------------
@app.get("/db-check")
def db_check():
    try:
        from database import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"db": "ok"}
    except Exception as e:
        return {"db": "error", "detail": str(e)}

# -----------------------------------------------
# Webhook de WhatsApp
# -----------------------------------------------
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

        # Obtener el ID del número de WhatsApp que recibió el mensaje
        phone_number_id = entry["metadata"]["phone_number_id"]

        # Buscar la clínica correspondiente en la base de datos
        db = SessionLocal()
        clinica = db.query(Clinica).filter(Clinica.whatsapp_phone_id == phone_number_id).first()
        db.close()

        if not clinica:
            print("Clínica no encontrada para", phone_number_id)
            return {"status": "clínica no configurada"}

        # Procesar los mensajes (si los hay)
        if "messages" in entry:
            message = entry["messages"][0]
            phone = message["from"]
            text = message["text"]["body"]
            # Pasamos el calendar_id de la clínica al bot
            response_text = procesar_mensaje(text, phone, clinica.google_calendar_id)
            send_whatsapp_message(phone, response_text)

    except Exception as e:
        print("Error procesando mensaje:", e)
    return {"status": "ok"}

# -----------------------------------------------
# Función para enviar mensajes de WhatsApp
# -----------------------------------------------
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