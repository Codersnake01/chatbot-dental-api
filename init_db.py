from database import engine, Base
from models import Clinica, Paciente, Cita

Base.metadata.create_all(bind=engine)
print("Tablas creadas correctamente")