import os
from fastapi import FastAPI, Request, Query
from fastapi.responses import PlainTextResponse
import requests
from dotenv import load_dotenv
from sqlalchemy import text
from datetime import datetime, timedelta

from database import SessionLocal
from models import Clinica, Paciente, Cita
from bot import procesar_mensaje

# Cargar variables de entorno solo en local
if not os.getenv("RENDER"):
    load_dotenv()

app = FastAPI()

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
CRON_SECRET = os.getenv("CRON_SECRET", "supersecreto")

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
        phone_number_id = entry["metadata"]["phone_number_id"]

        db = SessionLocal()
        clinica = db.query(Clinica).filter(Clinica.whatsapp_phone_id == phone_number_id).first()

        if not clinica:
            db.close()
            print("Clínica no encontrada para", phone_number_id)
            return {"status": "clínica no configurada"}

        ahora = datetime.utcnow()
        # Verificar período de prueba o membresía activa
        if not clinica.activa:
            if not clinica.fecha_fin_prueba or ahora > clinica.fecha_fin_prueba:
                db.close()
                return {"status": "período de prueba expirado o clínica inactiva"}

        if "messages" in entry:
            message = entry["messages"][0]
            phone = message["from"]
            text = message["text"]["body"]
            response_text = procesar_mensaje(text, phone, clinica.google_calendar_id)
            send_whatsapp_message(phone, response_text)

        db.close()
    except Exception as e:
        print("Error procesando mensaje:", e)
    return {"status": "ok"}

# -----------------------------------------------
# Endpoint de recordatorios de cita (24h antes)
# -----------------------------------------------
@app.post("/send-reminders")
def send_reminders(secret: str = Query(...)):
    if secret != CRON_SECRET:
        return {"error": "No autorizado"}, 403

    ahora = datetime.utcnow()
    ventana_inicio = ahora + timedelta(hours=24) - timedelta(minutes=5)
    ventana_fin = ahora + timedelta(hours=24) + timedelta(minutes=5)

    db = SessionLocal()
    clinicas = db.query(Clinica).all()
    recordatorios_cita = 0
    avisos_prueba = 0

    for clinica in clinicas:
        # Solo operar con clínicas activas o en prueba vigente
        if not clinica.activa and (not clinica.fecha_fin_prueba or ahora > clinica.fecha_fin_prueba):
            continue

        # 1. Recordatorios de cita (24h ±5min)
        citas = db.query(Cita).filter(
            Cita.clinica_id == clinica.id,
            Cita.fecha_hora >= ventana_inicio,
            Cita.fecha_hora <= ventana_fin,
            Cita.recordatorio_enviado == False
        ).all()

        for cita in citas:
            paciente = db.query(Paciente).filter(Paciente.id == cita.paciente_id).first()
            if not paciente:
                continue
            hora_str = cita.fecha_hora.strftime("%H:%M")
            mensaje = f"🦷 Recordatorio: tienes una cita dental mañana a las {hora_str}. ¡Te esperamos!"
            send_whatsapp_message(paciente.telefono, mensaje)
            cita.recordatorio_enviado = True
            recordatorios_cita += 1

        # 2. Aviso de vencimiento de prueba (48h antes)
        if not clinica.activa and clinica.fecha_fin_prueba and clinica.telefono_admin:
            # Solo si la prueba terminará en 48 horas (±5 min para que se procese en algún momento del día)
            aviso_ventana = ahora + timedelta(hours=48)
            diferencia = clinica.fecha_fin_prueba - aviso_ventana
            if timedelta(minutes=0) <= diferencia <= timedelta(minutes=10):
                mensaje_prueba = (
                    "⚠️ Tu período de prueba de DentalBot finaliza en 48 horas. "
                    "Para seguir usando el chatbot, realiza el pago de $90 por transferencia "
                    "y envía el comprobante al +595XXXXXXXX. ¡Gracias!"
                )
                send_whatsapp_message(clinica.telefono_admin, mensaje_prueba)
                avisos_prueba += 1

    db.commit()
    db.close()
    return {
        "recordatorios_cita": recordatorios_cita,
        "avisos_prueba": avisos_prueba
    }

# -----------------------------------------------
# Endpoint de activación manual de una clínica
# -----------------------------------------------
@app.post("/activar-clinica/{clinica_id}")
def activar_clinica(clinica_id: int, dias: int = 30, secret: str = Query(...)):
    if secret != CRON_SECRET:
        return {"error": "No autorizado"}, 403
    db = SessionLocal()
    clinica = db.query(Clinica).filter(Clinica.id == clinica_id).first()
    if not clinica:
        db.close()
        return {"error": "Clínica no encontrada"}, 404
    clinica.activa = True
    clinica.fecha_fin_prueba = datetime.utcnow() + timedelta(days=dias)
    db.commit()
    db.close()
    return {
        "mensaje": f"Clínica {clinica.nombre} activada por {dias} días",
        "vence": (datetime.utcnow() + timedelta(days=dias)).isoformat()
    }

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