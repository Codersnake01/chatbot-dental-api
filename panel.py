import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
from database import SessionLocal
from models import Clinica, Paciente, Cita

st.set_page_config(page_title="Panel del Dentista", page_icon="🦷", layout="wide")

if "clinica_id" not in st.session_state:
    st.session_state.clinica_id = None

# ---------- Registro / Login ----------
if st.session_state.clinica_id is None:
    st.title("🦷 DentalBot - Panel del Dentista")
    opcion = st.radio("Selecciona una opción", ["Iniciar sesión", "Registrar nueva clínica"])

    if opcion == "Registrar nueva clínica":
        nombre = st.text_input("Nombre de la clínica")
        whatsapp_id = st.text_input("Phone Number ID de WhatsApp Business")
        calendar_id = st.text_input("ID del calendario de Google")
        telefono_admin = st.text_input("Tu número de WhatsApp (para notificaciones)")
        if st.button("Registrar"):
            if not nombre or not whatsapp_id or not calendar_id:
                st.error("Completa todos los campos obligatorios.")
            else:
                db = SessionLocal()
                nueva = Clinica(
                    nombre=nombre,
                    whatsapp_phone_id=whatsapp_id,
                    google_calendar_id=calendar_id,
                    telefono_admin=telefono_admin,
                    fecha_fin_prueba=datetime.now(timezone.utc) + timedelta(days=14),  # <-- aware datetime
                    activa=False
                )
                db.add(nueva)
                db.commit()
                db.refresh(nueva)
                st.session_state.clinica_id = nueva.id
                db.close()
                st.success("¡Registrado con éxito! Tienes 2 semanas de prueba gratuita.")
                st.rerun()
    else:
        clinica_id = st.text_input("ID de la clínica")
        if st.button("Entrar"):
            if clinica_id:
                st.session_state.clinica_id = int(clinica_id)
                st.rerun()
    st.stop()

# ---------- Panel principal ----------
db = SessionLocal()
clinica = db.query(Clinica).filter(Clinica.id == st.session_state.clinica_id).first()

if not clinica:
    st.error("Clínica no encontrada.")
    db.close()
    st.stop()

st.title(f"🦷 {clinica.nombre} – Panel de Citas")

# Aviso de vencimiento de prueba
if not clinica.activa and clinica.fecha_fin_prueba:
    ahora = datetime.now(timezone.utc)                 # aware datetime
    dias_restantes = (clinica.fecha_fin_prueba - ahora).days   # ambos aware
    if dias_restantes <= 3:
        st.warning(
            f"⚠️ Tu período de prueba vence en {dias_restantes} día(s). "
            "Para continuar usando el chatbot, realiza una transferencia de $90 "
            "a la cuenta que te indicamos y envía el comprobante al +595992580622. "
            "Luego activaremos tu membresía."
        )

# Filtro por estado
estado_filtro = st.selectbox("Filtrar por estado", ["Todas", "pendiente", "confirmada", "cancelada"])
query = db.query(Cita, Paciente).join(Paciente, Cita.paciente_id == Paciente.id)\
    .filter(Cita.clinica_id == clinica.id)
if estado_filtro != "Todas":
    query = query.filter(Cita.estado == estado_filtro)

citas = query.order_by(Cita.fecha_hora.asc()).all()

if not citas:
    st.info("No hay citas registradas todavía.")
else:
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

# Métricas
st.markdown("---")
st.subheader("📊 Métricas")
col1, col2, col3 = st.columns(3)
total_citas = db.query(Cita).filter(Cita.clinica_id == clinica.id).count()
pendientes = db.query(Cita).filter(Cita.clinica_id == clinica.id, Cita.estado == "pendiente").count()
recordatorios = db.query(Cita).filter(Cita.clinica_id == clinica.id, Cita.recordatorio_enviado == True).count()
col1.metric("Total citas", total_citas)
col2.metric("Pendientes", pendientes)
col3.metric("Recordatorios enviados", recordatorios)

db.close()