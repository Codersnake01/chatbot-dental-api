from calendar_service import create_event, list_upcoming_events

# Reemplaza esto con el ID real de tu calendario "Consultorio Dental"
CALENDAR_ID = '5fc6082eaad7b22dc1b73c2b9ad62a0ad6b7ebccf83379f207ed955cdb610e1e@group.calendar.google.com'

# Crear una cita de prueba
event = create_event(
    CALENDAR_ID,
    summary='Cita de prueba - Paciente Test',
    start_time='2026-06-05T15:00:00',
    end_time='2026-06-05T16:00:00',
    description='Prueba de integración con chatbot dental'
)
print('✅ Evento creado:', event.get('htmlLink'))

# Listar próximos eventos
print('\n📅 Próximos eventos:')
events = list_upcoming_events(CALENDAR_ID)
for e in events:
    start = e['start'].get('dateTime', e['start'].get('date'))
    print(f"- {e.get('summary', 'Sin título')} ({start})")