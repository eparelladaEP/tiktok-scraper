#!/bin/bash

# Instalar Playwright y sus dependencias
playwright install --with-deps

# Forzar instalación de Chromium en el entorno de Streamlit Cloud
playwright install chromium

# Verificar la instalación de Chromium
ls -lah /home/appuser/.cache/ms-playwright/

# Mostrar la ubicación de los ejecutables de Playwright
which playwright
