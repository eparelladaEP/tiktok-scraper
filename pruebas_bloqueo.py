import requests
import streamlit as st

st.title("🌍 Verificación de IP pública de Streamlit Cloud")

try:
    response = requests.get("https://api64.ipify.org?format=json")
    ip_info = response.json()
    st.write(f"📌 La IP pública de Streamlit Cloud es: `{ip_info['ip']}`")
except:
    st.error("❌ No se pudo obtener la IP pública de Streamlit Cloud.")
