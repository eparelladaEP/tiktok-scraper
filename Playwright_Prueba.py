import sys
import streamlit as st
import pandas as pd
import asyncio
import nest_asyncio  # Evita problemas en Streamlit con async
from datetime import datetime
import base64
import os
import subprocess
import random
from playwright.async_api import async_playwright  # ✅ Importar la versión correcta de Playwright

# Ejecutar setup.sh automáticamente al iniciar la app en Streamlit Cloud
os.system("bash setup.sh")

# ✅ Instalar Playwright y Chromium si no están presentes
if not os.path.exists("/home/adminuser/.cache/ms-playwright/chromium-1155"):
    subprocess.run(["playwright", "install", "chromium"], check=True)

# 🔹 Aplicar `nest_asyncio` para evitar conflictos con asyncio en Streamlit
nest_asyncio.apply()

# 📌 Función para convertir el ID del video en fecha
def tiktok_id_to_date(video_id):
    binary_id = bin(int(video_id))[2:].zfill(64)
    timestamp_binary = binary_id[:32]
    timestamp = int(timestamp_binary, 2)
    return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d')

# 📌 Función para convertir valores con 'K' y 'M' en numéricos
def convert_to_number(value):
    if isinstance(value, str):
        value = value.replace(",", "")  
        if "K" in value:
            return float(value.replace("K", "")) * 1_000
        elif "M" in value:
            return float(value.replace("M", "")) * 1_000_000
        elif value.isdigit():
            return int(value)
    return 0  

# 📌 Extraer datos de TikTok con Playwright
async def get_tiktok_data(username, num_videos=None, date_range=None, include_pinned=True):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=[
            "--no-sandbox", "--disable-dev-shm-usage", "--single-process"
        ])
        page = await browser.new_page()

        # 🔹 Rotación de User-Agent
        USER_AGENTS = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        ]
        await page.set_user_agent(random.choice(USER_AGENTS))

        url = f"https://www.tiktok.com/@{username}"
        await page.goto(url, timeout=60000)

        # 🔹 Simulación de actividad humana para evitar bloqueos
        await page.mouse.move(random.randint(50, 300), random.randint(50, 300))
        await page.mouse.click(random.randint(100, 500), random.randint(100, 500))
        await asyncio.sleep(random.uniform(3, 6))  # Pausa aleatoria antes de extraer datos

        profile_data = {"Username": username}

        # 📌 Extraer información del perfil con manejo de errores
        try:
            profile_data["Name"] = await page.inner_text("h1[data-e2e='user-title']")
        except:
            profile_data["Name"] = "N/A"

        try:
            profile_data["Bio"] = await page.inner_text("h2[data-e2e='user-bio']")
        except:
            profile_data["Bio"] = "N/A"

        try:
            followers = await page.inner_text("strong[data-e2e='followers-count']")
            profile_data["Followers"] = followers
        except:
            profile_data["Followers"] = "N/A"
        
        # 📌 Extraer información de los vídeos
        video_elements = await page.query_selector_all("div[data-e2e='user-post-item']")
        video_data = []

        for idx, video in enumerate(video_elements, start=1):
            try:
                link_element = await video.query_selector("a")
                link = await link_element.get_attribute("href")
                video_id = link.split("/")[-1]
                date = tiktok_id_to_date(video_id)

                # 📌 Detectar si el video está anclado
                pinned = "Yes" if await video.query_selector("div[data-e2e='video-card-badge']") else "No"

                # 📌 Filtrar según configuración del usuario
                if not include_pinned and pinned == "Yes":
                    continue  

                # 📌 Filtrar por fecha si se seleccionó periodo de análisis
                if date_range and len(date_range) == 2:
                    start_date, end_date = date_range
                    if not (start_date.strftime('%Y-%m-%d') <= date <= end_date.strftime('%Y-%m-%d')):
                        continue

                # 📌 Extraer Views directamente desde el video en el perfil
                try:
                    views_element = await video.query_selector("strong[data-e2e='video-views']")
                    views = convert_to_number(await views_element.inner_text()) if views_element else 0
                except:
                    views = 0

                # 📌 Abrir el video en nueva pestaña para obtener métricas
                video_page = await browser.new_page()
                await video_page.goto(link)
                await asyncio.sleep(random.uniform(5, 10))  # 🔹 Espera aleatoria para evitar bloqueos

                async def safe_extract(selector):
                    try:
                        element = await video_page.query_selector(selector)
                        return convert_to_number(await element.inner_text()) if element else 0
                    except:
                        return 0

                likes = await safe_extract("strong[data-e2e='like-count']")
                comments = await safe_extract("strong[data-e2e='comment-count']")
                shares = await safe_extract("strong[data-e2e='share-count']")
                saves = await safe_extract("strong[data-e2e='undefined-count']")

                video_data.append({
                    "Link": link,
                    "Date": date,
                    "Pinned": pinned,
                    "Views": views,
                    "Likes": likes,
                    "Comments": comments,
                    "Shares": shares,
                    "Saves": saves
                })

                await video_page.close()

                if num_videos and len(video_data) >= num_videos:
                    break  
            except:
                continue

        await browser.close()
        return profile_data, video_data

# 📌 Interfaz con Streamlit
st.title("📌 Analiza una cuenta de TikTok")

# 📌 Input de usuario
username = st.text_input("Introduce el nombre de usuario de TikTok:")
option = st.radio("¿Cómo deseas analizar los vídeos?", ["Cantidad de vídeos", "Rango de fechas"])
include_pinned = st.checkbox("Incluir vídeos anclados", value=True)

if option == "Cantidad de vídeos":
    num_videos = st.slider("Número de vídeos a analizar:", 1, 50, 10)
    date_range = None
else:
    num_videos = None
    date_range = st.date_input("Selecciona el rango de fechas", [datetime.today(), datetime.today()])

# 📌 Inicializar session_state si no existe
for key in ["last_username", "videos", "profile"]:
    if key not in st.session_state:
        st.session_state[key] = None

if st.button("Obtener Datos") and username:
    with st.spinner("Obteniendo datos..."):
        # Resetear datos solo si el usuario cambia
        if st.session_state.last_username is None or username != st.session_state.last_username:
            st.session_state.last_username = username
            st.session_state.videos = None
            st.session_state.profile = None


        if sys.platform == "win32":
            loop = asyncio.ProactorEventLoop()
            asyncio.set_event_loop(loop)
            profile, videos = loop.run_until_complete(get_tiktok_data(username, num_videos, date_range, include_pinned))
        else:
            profile, videos = asyncio.run(get_tiktok_data(username, num_videos, date_range, include_pinned))

        st.session_state.profile = profile
        st.session_state.videos = videos

        st.subheader("📌 Perfil del Usuario")
        st.json(profile)
        
        df = pd.DataFrame(videos)

        # 📌 Calcular Engagements y ER
        df["Engagements"] = df["Likes"] + df["Comments"] + df["Shares"] + df["Saves"]
        df["ER"] = ((df["Engagements"] / df["Views"]) * 100).round(2).astype(str) + "%"


        # 📌 Mostrar tabla en Streamlit
        st.subheader("📌 Datos de vídeos extraídos")
        st.dataframe(df)

        # 📌 Calcular TARGET CPMs
        avg_cpm_15 = df["Views"].mean() * 0.015
        avg_cpm_20 = df["Views"].mean() * 0.020
        median_cpm_15 = df["Views"].median() * 0.015
        median_cpm_20 = df["Views"].median() * 0.020

        # Calcular AVG y MEDIAN views, Engagement y ER%
        avg_views = df["Views"].mean()
        avg_engagements = df["Engagements"].mean()
        avg_ER = df["ER"].str.replace('%', '').astype(float).mean()  # Quitar '%' antes de convertir a float
        median_views = df["Views"].median()
        median_engagements = df["Engagements"].median()
        median_ER = df["ER"].str.replace('%', '').astype(float).median()  # Quitar '%' antes de convertir a float

        # 📊 Mostrar Medias y Medianas de KPIs
        st.write(f"**Views Medias:** {avg_views:.0f}".replace(',', '.'))
        st.write(f"**Engagements Medias:** {avg_engagements:.0f}".replace(',', '.'))
        st.write(f"**ER Medio:** {avg_ER:.2f} %")
        st.write(f"**Views Medianas:** {median_views:.0f}".replace(',', '.'))
        st.write(f"**Engagements Medianas:** {median_engagements:.0f}".replace(',', '.'))
        st.write(f"**ER Mediano:** {median_ER:.2f} %")

        # 📌 Mostrar cálculos
        st.subheader("📊 Costes Objetivo")
        st.write(f"**TARGET (PROMEDIO) CPM 15:** {avg_cpm_15:.2f} €")
        st.write(f"**TARGET (PROMEDIO) CPM 20:** {avg_cpm_20:.2f} €")
        st.write(f"**TARGET (MEDIANA) CPM 15:** {median_cpm_15:.2f} €")
        st.write(f"**TARGET (MEDIANA) CPM 20:** {median_cpm_20:.2f} €")

        # 📌 Guardamos los datos en session_state para evitar recarga al descargar
        if "df" not in st.session_state:
            st.session_state.df = df

        if "kpis_data" not in st.session_state:
            st.session_state.kpis_data = pd.DataFrame([{
                "AVG Views": f"{avg_views:.0f}".replace(',', '.'),
                "AVG Engagements": f"{avg_engagements:.0f}".replace(',', '.'),
                "AVG ER (%)": f"{avg_ER:.2f}",
                "MEDIAN Views": f"{median_views:.0f}".replace(',', '.'),
                "MEDIAN Engagements": f"{median_engagements:.0f}".replace(',', '.'),
                "MEDIAN ER (%)": f"{median_ER:.2f}"
            }])

        if "costes_data" not in st.session_state:
            st.session_state.costes_data = pd.DataFrame([{
                "TARGET (PROMEDIO) CPM 15 (€)": f"{avg_cpm_15:.2f}",
                "TARGET (PROMEDIO) CPM 20 (€)": f"{avg_cpm_20:.2f}",
                "TARGET (MEDIANA) CPM 15 (€)": f"{median_cpm_15:.2f}",
                "TARGET (MEDIANA) CPM 20 (€)": f"{median_cpm_20:.2f}"
            }])

        # 📌 Función para generar enlaces de descarga sin refrescar la app
        def get_download_link(df, filename):
            csv = df.to_csv(index=False).encode()
            b64 = base64.b64encode(csv).decode()  # Codificar en base64
            return f'<a href="data:file/csv;base64,{b64}" download="{filename}">📥 Descargar {filename}</a>'

        # 📥 Mostrar enlaces de descarga SIN RECARGA
        st.markdown(get_download_link(st.session_state.df, f"{username}_videos.csv"), unsafe_allow_html=True)
        st.markdown(get_download_link(st.session_state.kpis_data, f"{username}_kpis.csv"), unsafe_allow_html=True)
        st.markdown(get_download_link(st.session_state.costes_data, f"{username}_costes.csv"), unsafe_allow_html=True)

        # 🔄 Botón manual para refrescar la búsqueda
        if st.button("🔄 Refrescar Búsqueda"):
            for key in ["df", "kpis_data", "costes_data", "videos", "profile", "last_username"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.experimental_rerun()

