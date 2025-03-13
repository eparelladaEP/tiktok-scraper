import sys
import streamlit as st
import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
from io import BytesIO

# Inicializar session_state si no existe
if "last_username" not in st.session_state:
    st.session_state.last_username = ""
if "videos" not in st.session_state:
    st.session_state.videos = None
if "profile" not in st.session_state:
    st.session_state.profile = None

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

# 📌 Configurar Selenium
def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--log-level=3")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

# 📌 Extraer datos de TikTok
def get_tiktok_data(username, num_videos=None, date_range=None, include_pinned=True):
    driver = setup_driver()
    url = f"https://www.tiktok.com/@{username}"
    driver.get(url)
    time.sleep(5)
    
    profile_data = {"Username": username}

    # 📌 Extraer información del perfil
    try:
        profile_data["Name"] = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1[data-e2e='user-title']"))
        ).text
    except:
        profile_data["Name"] = "N/A"

    try:
        profile_data["Bio"] = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h2[data-e2e='user-bio']"))
        ).text
    except:
        profile_data["Bio"] = "N/A"

    try:
        followers = driver.find_elements(By.CSS_SELECTOR, "strong[data-e2e='followers-count']")
        profile_data["Followers"] = followers[0].text if followers else "N/A"
    except:
        profile_data["Followers"] = "N/A"
    
    # 📌 Extraer información de los vídeos
    videos = driver.find_elements(By.CSS_SELECTOR, "div[data-e2e='user-post-item']")
    video_data = []
    
    for idx, video in enumerate(videos, start=1):  
        try:
            link = video.find_element(By.TAG_NAME, "a").get_attribute("href")
            video_id = link.split("/")[-1]
            date = tiktok_id_to_date(video_id)  

            # 📌 Detectar si el video está anclado
            try:
                video.find_element(By.CSS_SELECTOR, "div[data-e2e='video-card-badge']")
                pinned = "Yes"
            except:
                pinned = "No"

            # 📌 Filtrar según configuración del usuario
            if not include_pinned and pinned == "Yes":
                continue  

            # 📌 Filtrar por fecha si se seleccionó periodo de análisis
            if date_range:
                start_date, end_date = date_range
                if not (start_date.strftime('%Y-%m-%d') <= date <= end_date.strftime('%Y-%m-%d')):
                    continue  

            # 📌 Extraer Views directamente desde el video en el perfil
            try:
                views = video.find_element(By.CSS_SELECTOR, "strong[data-e2e='video-views']").text
                views = convert_to_number(views)
            except:
                views = 0

            # 📌 Abrir el video en nueva pestaña para obtener descripción y métricas
            driver.execute_script("window.open(arguments[0]);", link)
            driver.switch_to.window(driver.window_handles[1])
            time.sleep(5)

            # 📌 Extraer métricas
            def safe_extract(selector):
                try:
                    return WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    ).text
                except:
                    return "0"

            likes = convert_to_number(safe_extract("strong[data-e2e='like-count']"))
            comments = convert_to_number(safe_extract("strong[data-e2e='comment-count']"))
            shares = convert_to_number(safe_extract("strong[data-e2e='share-count']"))
            saves = convert_to_number(safe_extract("strong[data-e2e='undefined-count']"))

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
            
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            time.sleep(5)

            if num_videos and len(video_data) >= num_videos:
                break  
        except:
            continue
    
    driver.quit()
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

if st.button("Obtener Datos") and username:
    with st.spinner("Obteniendo datos..."):
        # Resetear datos solo si el usuario cambia
        if username != st.session_state.last_username:
            st.session_state.last_username = username
            st.session_state.videos = None
            st.session_state.profile = None

        profile, videos = get_tiktok_data(username, num_videos, date_range, include_pinned)

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

        df["ER_float"] = ((df["Engagements"] / df["Views"]) * 100).round(2)  # Guardamos en float
        df["ER"] = df["ER_float"].astype(str) + "%"  # La versión para mostrar con "%"

        # Calcular AVG y MEDIAN views, Engagement y ER%
        avg_views = df["Views"].mean()
        avg_engagements = df["Engagements"].mean()
        avg_ER = df["ER_float"].astype(float).mean()
        median_views = df["Views"].median()
        median_engagements = df["Engagements"].median()
        median_ER = df["ER_float"].astype(float).median()

        #Mostrar Medias y Medianas de KPIs
        st.subheader("📊 Medias y Medianas KPIs")
        st.write(f"**Views Medias:** {avg_views:,.0f}")
        st.write(f"**Engagements Medias:** {avg_engagements:,.0f}")
        st.write(f"**ER Medio:** {avg_ER:.2f} %")
        st.write(f"**Views Medianas:** {median_views:,.0f}")
        st.write(f"**Engagements Medianas:** {median_engagements:,.0f}")
        st.write(f"**ER Mediano:** {median_ER:.2f} %")


        # 📌 Mostrar cálculos
        st.subheader("📊 Costes Objetivo")
        st.write(f"**TARGET (PROMEDIO) CPM 15:** {avg_cpm_15:.2f} €")
        st.write(f"**TARGET (PROMEDIO) CPM 20:** {avg_cpm_20:.2f} €")
        st.write(f"**TARGET (MEDIANA) CPM 15:** {median_cpm_15:.2f} €")
        st.write(f"**TARGET (MEDIANA) CPM 20:** {median_cpm_20:.2f} €")

        # 📥 Descargar CSV 
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Descargar CSV", csv, f"{username}_tiktok_data.csv", "text/csv")