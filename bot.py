from datetime import datetime, timedelta
import re
import calendar_service  # nuestro módulo de Google Calendar

# Diccionario temporal para guardar el estado de la conversación.
# En producción lo almacenaremos en la base de datos.
estado_usuarios = {}

# ID del calendario de prueba (más adelante será por clínica)
CALENDARIO_ID = '5fc6082eaad7b22dc1b73c2b9ad62a0ad6b7ebccf83379f207ed955cdb610e1e@group.calendar.google.com'

def procesar_mensaje(text: str, user_id: str) -> str:
    """Procesa el mensaje del paciente y devuelve la respuesta del bot."""
    texto = text.strip()
    
    # --- Si el usuario está en medio de un flujo de cita ---
    if user_id in estado_usuarios:
        paso = estado_usuarios[user_id]
        
        if paso == 'ESPERANDO_FECHA':
            # Intentar interpretar la fecha y hora
            fecha_hora = parsear_fecha_hora(texto)
            if fecha_hora:
                # Crear la cita en Google Calendar
                inicio = fecha_hora.isoformat()
                fin = (fecha_hora + timedelta(hours=1)).isoformat()
                try:
                    evento = calendar_service.create_event(
                        CALENDARIO_ID,
                        summary='Cita dental',
                        start_time=inicio,
                        end_time=fin,
                        description=f'Paciente: {user_id}'
                    )
                    # Limpiar estado
                    del estado_usuarios[user_id]
                    return (f"✅ Cita agendada para el {fecha_hora.strftime('%d/%m/%Y a las %H:%M')}.\n"
                            f"Recibirás un recordatorio. ¡Gracias por confiar en nosotros!")
                except Exception as e:
                    print("Error al crear evento:", e)
                    return "❌ Hubo un problema al agendar la cita. Por favor, intenta de nuevo más tarde."
            else:
                return "❌ No pude entender la fecha y hora. Usa el formato:\n📅 AAAA-MM-DD HH:MM\nEjemplo: 2026-06-15 10:30"
    
    # --- Palabras clave iniciales ---
    texto_lower = texto.lower()
    
    if any(p in texto_lower for p in ["cita", "agendar", "turno", "hora"]):
        estado_usuarios[user_id] = 'ESPERANDO_FECHA'
        return ("¿Para qué día y hora quieres la cita?\n"
                "Por favor, escríbelo así:\n"
                "📅 AAAA-MM-DD HH:MM\n"
                "Ejemplo: 2026-06-15 10:30")
    
    elif any(p in texto_lower for p in ["dolor", "duele", "urgencia", "emergencia"]):
        return "Lamento tu molestia. ¿Tienes hinchazón o fiebre? (Sí/No) Para darte prioridad."
    
    elif any(p in texto_lower for p in ["precio", "costo", "cuánto"]):
        return "Puedes consultar precios orientativos: limpieza dental desde 30 USD, ortodoncia desde 80 USD. ¿Te interesa algo?"
    
    else:
        return ("Hola, soy el asistente virtual de Clínica Dental. Puedo:\n"
                "🔹 Agendar citas\n"
                "🔹 Atender urgencias\n"
                "🔹 Consultar precios\n"
                "¿En qué te ayudo?")


def parsear_fecha_hora(texto: str):
    """
    Intenta convertir un texto en un objeto datetime.
    Soporta formatos como:
    - 2026-06-15 10:30
    - 15/06/2026 10:30
    - 15-06-2026 10:30
    """
    # Limpiar el texto
    texto = texto.strip()
    # Reemplazar '/' o '-' por '-'
    texto = texto.replace('/', '-').replace('.', '-')
    # Formatos a probar
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