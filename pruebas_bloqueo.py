import os
import streamlit as st

st.title("🔍 Test con `curl` a TikTok")

try:
    result = os.popen("curl -I https://www.tiktok.com").read()
    st.code(result)
except:
    st.error("❌ No se pudo ejecutar `curl` en Streamlit Cloud.")

