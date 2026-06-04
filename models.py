from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from database import Base

class Clinica(Base):
    __tablename__ = "clinicas"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    whatsapp_phone_id = Column(String, unique=True, nullable=False)
    google_calendar_id = Column(String)
    configuracion = Column(String)
    fecha_fin_prueba = Column(DateTime, nullable=True)
    activa = Column(Boolean, default=False)
    telefono_admin = Column(String, nullable=True)   # Para notificaciones de vencimiento

class Paciente(Base):
    __tablename__ = "pacientes"
    id = Column(Integer, primary_key=True, index=True)
    telefono = Column(String, unique=True, index=True)
    nombre = Column(String)
    email = Column(String)

class Cita(Base):
    __tablename__ = "citas"
    id = Column(Integer, primary_key=True, index=True)
    clinica_id = Column(Integer, ForeignKey("clinicas.id"))
    paciente_id = Column(Integer, ForeignKey("pacientes.id"))
    fecha_hora = Column(DateTime)
    estado = Column(String, default="pendiente")
    motivo = Column(String)
    recordatorio_enviado = Column(Boolean, default=False)