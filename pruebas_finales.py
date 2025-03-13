import sys
import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import pandas as pd

# 📌 Configurar Selenium para Streamlit
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
def get_tiktok_data(username):
    driver = setup_driver()
    url = f"https://www.tiktok.com/@{username}"
    driver.get(url)
    time.sleep(5)
    
    profile_data = {"Username": username}
    
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
    
    videos = driver.find_elements(By.CSS_SELECTOR, "div[data-e2e='user-post-item']")
    video_data = []
    
    for video in videos[:10]:
        try:
            link = video.find_element(By.TAG_NAME, "a").get_attribute("href")
            views = video.text.split("\n")[0]

            driver.execute_script("window.open(arguments[0]);", link)
            driver.switch_to.window(driver.window_handles[1])
            time.sleep(5)

            # 📌 Extraer la descripción
            try:
                description_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'h1[data-e2e="browse-video-desc"]'))
                )
                description = description_element.text.strip()
            except:
                description = "N/A"

            # 📌 Extraer la fecha
            try:
                date_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'span[data-e2e="browser-nickname"] span'))
                )
                date = date_element.text.strip()
            except:
                date = "N/A"

            # 📌 Extraer métricas
            try:
                likes = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "strong[data-e2e='like-count']"))
                ).text
            except:
                likes = "0"

            try:
                comments = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "strong[data-e2e='comment-count']"))
                ).text
            except:
                comments = "0"

            try:
                shares = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "strong[data-e2e='share-count']"))
                ).text
            except:
                shares = "0"

            try:
                saves = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "strong[data-e2e='undefined-count']"))
                ).text
            except:
                saves = "0"
            
            video_data.append({
                "Link": link,
                "Date": date,
                "Description": description,
                "Views": views,
                "Likes": likes,
                "Comments": comments,
                "Shares": shares,
                "Saves": saves
            })
            
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            time.sleep(3)
        except:
            continue
    
    driver.quit()
    return profile_data, video_data

# 📌 Interfaz con Streamlit
st.title("📌 Scraper de TikTok")
username = st.text_input("Introduce el nombre de usuario de TikTok:")

if st.button("Obtener Datos") and username:
    with st.spinner("Obteniendo datos..."):
        profile, videos = get_tiktok_data(username)
        st.subheader("📌 Perfil del Usuario")
        st.json(profile)
        
        # 📌 Convertir datos en DataFrame
        df = pd.DataFrame(videos)

        # 📌 Convertir valores con K y M
        def convert_values(value):
            if "K" in value:
                return float(value.replace("K", "")) * 1_000
            elif "M" in value:
                return float(value.replace("M", "")) * 1_000_000
            try:
                return float(value)
            except ValueError:
                return 0  # Manejo de errores

        # 📌 Aplicar conversión a las métricas
        for column in ["Views", "Likes", "Comments", "Shares", "Saves"]:
            df[column] = df[column].astype(str).apply(convert_values)

        # 📌 Calcular Engagements
        df["Engagements"] = df["Likes"] + df["Comments"] + df["Shares"] + df["Saves"]

        # 📌 Calcular ER para cada vídeo
        df["ER"] = ((df["Engagements"] / df["Views"]) * 100).round(2).astype(str) + "%"

        # 📌 Cálculo de AVERAGE CPM 15 y AVERAGE CPM 20
        avg_views = df["Views"].mean()
        avg_cpm_15 = (avg_views * 0.015)
        avg_cpm_20 = (avg_views * 0.020)

        # 📌 Cálculo de MEDIAN CPM 15 y MEDIAN CPM 20
        median_views = df["Views"].median()
        median_cpm_15 = (median_views * 0.015)
        median_cpm_20 = (median_views * 0.020)

        # 📌 Mostrar DataFrame en Streamlit
        st.subheader("📌 Datos de vídeos")
        st.dataframe(df)

        # 📌 Mostrar cálculos
        st.subheader("📊 Resumen de CPMs")
        st.write(f"**AVERAGE CPM 15:** {avg_cpm_15:.2f} €")
        st.write(f"**AVERAGE CPM 20:** {avg_cpm_20:.2f} €")
        st.write(f"**MEDIAN CPM 15:** {median_cpm_15:.2f} €")
        st.write(f"**MEDIAN CPM 20:** {median_cpm_20:.2f} €")

        # 📥 Descargar CSV
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Descargar CSV", csv, f"{username}_tiktok_data.csv", "text/csv", key="download-csv")
