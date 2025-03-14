#!/bin/bash

# Instalar Playwright y sus dependencias
playwright install --with-deps

# Instalar Chromium específicamente
playwright install chromium

# Verificar la instalación de Chromium
ls -lah /home/appuser/.cache/ms-playwright/

# Mostrar la ubicación de los ejecutables de Playwright
which playwright
