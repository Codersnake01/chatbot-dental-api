def procesar_mensaje(text: str) -> str:
    text = text.lower().strip()
    if any(p in text for p in ["cita", "agendar", "turno", "hora"]):
        return "Claro, ¿para qué día y hora te gustaría? (ejemplo: lunes 10 a las 15:00)"
    elif any(p in text for p in ["dolor", "duele", "urgencia", "emergencia"]):
        return "Lamento tu molestia. ¿Tienes hinchazón o fiebre? (Sí/No) Para darte prioridad."
    elif any(p in text for p in ["precio", "costo", "cuánto"]):
        return "Puedes consultar precios orientativos: limpieza dental desde 30 USD, ortodoncia desde 80 USD. ¿Te interesa algo?"
    else:
        return "Hola, soy el asistente virtual de Clínica Dental. Puedo agendar citas, orientarte en urgencias y consultar precios. ¿En qué te ayudo?"