from datetime import datetime, timedelta
import re
import calendar_service

# Modelos y base de datos
from database import SessionLocal
from models import Clinica, Paciente, Cita

# Diccionario temporal para el estado de la conversación.
# En producción se migrará a la base de datos.
estado_usuarios = {}


def procesar_mensaje(text: str, user_id: str, calendar_id: str) -> str:
    """Procesa el mensaje del paciente y devuelve la respuesta del bot."""
    texto = text.strip()

    # --- Si el usuario está en medio del flujo de cita ---
    if user_id in estado_usuarios:
        paso = estado_usuarios[user_id]

        if paso == 'ESPERANDO_FECHA':
            fecha_hora = parsear_fecha_hora(texto)
            if fecha_hora:
                inicio = fecha_hora.isoformat()
                fin = (fecha_hora + timedelta(hours=1)).isoformat()
                try:
                    # 1. Crear evento en Google Calendar
                    calendar_service.create_event(
                        calendar_id,
                        summary='Cita dental',
                        start_time=inicio,
                        end_time=fin,
                        description=f'Paciente: {user_id}'
                    )

                    # 2. Guardar la cita en la base de datos
                    db = SessionLocal()
                    # Buscar o crear paciente
                    paciente = db.query(Paciente).filter(
                        Paciente.telefono == user_id
                    ).first()
                    if not paciente:
                        paciente = Paciente(telefono=user_id)
                        db.add(paciente)
                        db.commit()
                        db.refresh(paciente)

                    # Obtener la clínica por su google_calendar_id
                    clinica = db.query(Clinica).filter(
                        Clinica.google_calendar_id == calendar_id
                    ).first()
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

                    # Limpiar estado
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
                    "❌ No pude entender la fecha y hora. Usa el formato:\n"
                    "📅 AAAA-MM-DD HH:MM\n"
                    "Ejemplo: 2026-06-15 10:30"
                )

    # --- Palabras clave iniciales ---
    texto_lower = texto.lower()

    if any(p in texto_lower for p in ["cita", "agendar", "turno", "hora"]):
        estado_usuarios[user_id] = 'ESPERANDO_FECHA'
        return (
            "¿Para qué día y hora quieres la cita?\n"
            "Por favor, escríbelo así:\n"
            "📅 AAAA-MM-DD HH:MM\n"
            "Ejemplo: 2026-06-15 10:30"
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


def parsear_fecha_hora(texto: str):
    """
    Intenta convertir un texto en un objeto datetime.
    Soporta formatos como:
    - 2026-06-15 10:30
    - 15/06/2026 10:30
    - 15-06-2026 10:30
    """
    texto = texto.strip()
    # Reemplazar '/' o '-' por '-'
    texto = texto.replace('/', '-').replace('.', '-')
    formatos = [
        '%Y-%m-%d %H:%M',
        '%d-%m-%Y %H:%M',
    ]
    for fmt in formatos:
        try:
            return datetime.strptime(texto, fmt)
        except ValueError:
            continue
    return None