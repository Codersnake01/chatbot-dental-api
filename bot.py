from datetime import datetime, timedelta
import re
import calendar_service
import dateparser

from database import SessionLocal
from models import Clinica, Paciente, Cita

estado_usuarios = {}

def procesar_mensaje(text: str, user_id: str, calendar_id: str) -> str:
    texto = text.strip()

    if user_id in estado_usuarios:
        paso = estado_usuarios[user_id]
        if paso == 'ESPERANDO_FECHA':
            fecha_hora = parsear_fecha_hora(texto)
            if fecha_hora:
                inicio = fecha_hora.isoformat()
                fin = (fecha_hora + timedelta(hours=1)).isoformat()
                try:
                    calendar_service.create_event(
                        calendar_id,
                        summary='Cita dental',
                        start_time=inicio,
                        end_time=fin,
                        description=f'Paciente: {user_id}'
                    )
                    db = SessionLocal()
                    paciente = db.query(Paciente).filter(Paciente.telefono == user_id).first()
                    if not paciente:
                        paciente = Paciente(telefono=user_id)
                        db.add(paciente)
                        db.commit()
                        db.refresh(paciente)
                    clinica = db.query(Clinica).filter(Clinica.google_calendar_id == calendar_id).first()
                    if clinica:
                        nueva_cita = Cita(
                            clinica_id=clinica.id,
                            paciente_id=paciente.id,
                            fecha_hora=fecha_hora,
                            estado="pendiente",
                            motivo="Cita dental"
                        )
                        db.add(nueva_cita)
                        db.commit()
                    db.close()
                    del estado_usuarios[user_id]
                    return (
                        f"✅ Cita agendada para el "
                        f"{fecha_hora.strftime('%d/%m/%Y a las %H:%M')}.\n"
                        f"Recibirás un recordatorio. ¡Gracias por confiar en nosotros!"
                    )
                except Exception as e:
                    print("Error al crear evento o guardar cita:", e)
                    return "❌ Hubo un problema al agendar la cita. Por favor, intenta de nuevo más tarde."
            else:
                return (
                    "❌ No pude entender la fecha y hora. Intenta con:\n"
                    "📌 mañana a las 10\n"
                    "📌 el lunes a las 3 pm\n"
                    "📌 2026-06-15 10:30"
                )

    texto_lower = texto.lower()
    if any(p in texto_lower for p in ["cita", "agendar", "turno", "hora"]):
        estado_usuarios[user_id] = 'ESPERANDO_FECHA'
        return (
            "¿Para qué día y hora quieres la cita?\n"
            "Puedes escribirlo de forma natural, por ejemplo:\n"
            "📅 mañana a las 10\n"
            "📅 el lunes a las 3 pm\n"
            "📅 2026-06-15 10:30"
        )
    elif any(p in texto_lower for p in ["dolor", "duele", "urgencia", "emergencia"]):
        return "Lamento tu molestia. ¿Tienes hinchazón o fiebre? (Sí/No) Para darte prioridad."
    elif any(p in texto_lower for p in ["precio", "costo", "cuánto"]):
        return "Puedes consultar precios orientativos: limpieza dental desde 30 USD, ortodoncia desde 80 USD. ¿Te interesa algo?"
    else:
        return (
            "Hola, soy el asistente virtual de Clínica Dental. Puedo:\n"
            "🔹 Agendar citas\n"
            "🔹 Atender urgencias\n"
            "🔹 Consultar precios\n"
            "¿En qué te ayudo?"
        )

def parsear_fecha_hora(texto: str) -> datetime | None:
    match = re.search(
        r'a las\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?',
        texto,
        re.IGNORECASE
    )
    if match:
        hora = int(match.group(1))
        minutos = int(match.group(2)) if match.group(2) else 0
        meridiano = match.group(3).lower() if match.group(3) else None
        if meridiano == 'pm' and hora < 12:
            hora += 12
        elif meridiano == 'am' and hora == 12:
            hora = 0

        texto_sin_hora = re.sub(
            r'a las\s+\d{1,2}(?::\d{2})?\s*(am|pm)?',
            '',
            texto,
            flags=re.IGNORECASE
        ).strip()

        fecha = dateparser.parse(
            texto_sin_hora,
            languages=['es'],
            settings={
                'TIMEZONE': 'America/Asuncion',
                'RETURN_AS_TIMEZONE_AWARE': False,
                'PREFER_DATES_FROM': 'future',
            }
        )
        if fecha:
            return fecha.replace(hour=hora, minute=minutos, second=0, microsecond=0)
        return None
    else:
        return dateparser.parse(
            texto,
            languages=['es'],
            settings={
                'TIMEZONE': 'America/Asuncion',
                'RETURN_AS_TIMEZONE_AWARE': False,
                'PREFER_DATES_FROM': 'future',
            }
        )