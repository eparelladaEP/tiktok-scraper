#!/bin/bash

# Instalar Playwright y sus dependencias
playwright install --with-deps

# Forzar instalación de Chromium en el entorno de Streamlit Cloud
playwright install chromium

# Crear la variable de entorno para forzar modo sin sandbox (Importante en Streamlit Cloud)
export PLAYWRIGHT_BROWSERS_PATH=0

# Verificar la instalación de Chromium
ls -lah /home/appuser/.cache/ms-playwright/

# Mostrar la ubicación de los ejecutables de Playwright
which playwright
