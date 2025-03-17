import requests
import streamlit as st

st.title("🔍 Test de conexión a TikTok desde Streamlit Cloud")

# URL del perfil de TikTok (puedes cambiarla por cualquier otra)
tiktok_url = "https://www.tiktok.com/@primevideoes"

try:
    response = requests.get(tiktok_url, timeout=10)
    status_code = response.status_code

    if status_code == 200:
        st.success("✅ TikTok responde correctamente desde Streamlit Cloud.")
    elif status_code == 403:
        st.error("❌ TikTok está bloqueando la IP de Streamlit Cloud. (Error 403)")
    elif status_code == 429:
        st.warning("⚠️ TikTok está limitando las peticiones (Error 429 - Too Many Requests).")
    else:
        st.error(f"⚠️ TikTok devolvió un código de estado inesperado: {status_code}")
except requests.exceptions.RequestException as e:
    st.error(f"❌ No se pudo conectar a TikTok: {str(e)}")
