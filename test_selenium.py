from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

# 📌 Configurar Selenium
def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Modo sin interfaz gráfica
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--log-level=3")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

# 📌 Extraer información de los vídeos anclados desde el perfil del usuario
def get_pinned_videos(username):
    driver = setup_driver()
    url = f"https://www.tiktok.com/@{username}"
    driver.get(url)
    time.sleep(5)

    video_data = []

    try:
        # Buscar todos los videos en la página del perfil
        videos = driver.find_elements(By.CSS_SELECTOR, "div[data-e2e='user-post-item']")

        for idx, video in enumerate(videos, start=1):
            try:
                # Obtener el enlace del vídeo
                link = video.find_element(By.TAG_NAME, "a").get_attribute("href")
                
                # Verificar si el video está anclado
                try:
                    video.find_element(By.CSS_SELECTOR, "div[data-e2e='video-card-badge']")
                    pinned = "Yes"
                except:
                    pinned = "No"

                video_data.append({
                    "Video #": idx,
                    "Link": link,
                    "Pinned": pinned
                })

            except:
                continue

    except:
        pass

    driver.quit()
    return video_data

# 📌 Solicitar usuario
username = input("Introduce el nombre de usuario de TikTok: ")
pinned_videos = get_pinned_videos(username)

# 📌 Mostrar resultados
print("\n📌 Resultados:")
if pinned_videos:
    for video in pinned_videos:
        print(f"Video {video['Video #']} - {video['Link']} - Pinned: {video['Pinned']}")
else:
    print("No se encontraron vídeos.")
