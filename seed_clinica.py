from database import SessionLocal
from models import Clinica

db = SessionLocal()
existe = db.query(Clinica).filter(Clinica.whatsapp_phone_id == "1158852253975054").first()
if existe:
    print("La clínica ya existe, no se inserta de nuevo.")
else:
    clinica = Clinica(
        nombre="Consultorio Dental",
        whatsapp_phone_id="1158852253975054",
        google_calendar_id="5fc6082eaad7b22dc1b73c2b9ad62a0ad6b7ebccf83379f207ed955cdb610e1e@group.calendar.google.com"
    )
    db.add(clinica)
    db.commit()
    print("Clínica de prueba agregada")
db.close()