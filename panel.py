import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database import SessionLocal
from models import Clinica, Paciente, Cita

# Configuración de la página
st.set_page_config(page_title="Panel del Dentista", page_icon="🦷", layout="wide")

# ID de la clínica de prueba (en producción se obtendrá tras un login)
CLINICA_PHONE_ID = "1158852253975054"

# Conectar a la base de datos
db = SessionLocal()
clinica = db.query(Clinica).filter(Clinica.whatsapp_phone_id == CLINICA_PHONE_ID).first()

if not clinica:
    st.error("❌ Clínica no encontrada. Verifica el identificador.")
    db.close()
    st.stop()

st.title(f"🦷 {clinica.nombre} – Panel de Citas")

# Filtro rápido por estado
estado_filtro = st.selectbox("Filtrar por estado", ["Todas", "pendiente", "confirmada", "cancelada"])

# Obtener citas de la clínica
query = db.query(Cita, Paciente).join(Paciente, Cita.paciente_id == Paciente.id)\
    .filter(Cita.clinica_id == clinica.id)

if estado_filtro != "Todas":
    query = query.filter(Cita.estado == estado_filtro)

citas = query.order_by(Cita.fecha_hora.asc()).all()

if not citas:
    st.info("No hay citas registradas todavía.")
else:
    # Construir tabla para mostrar
    data = []
    for cita, paciente in citas:
        data.append({
            "Fecha y hora": cita.fecha_hora.strftime("%d/%m/%Y %H:%M") if cita.fecha_hora else "Sin fecha",
            "Paciente": paciente.nombre or paciente.telefono,
            "Motivo": cita.motivo or "No especificado",
            "Estado": cita.estado
        })
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)

db.close()