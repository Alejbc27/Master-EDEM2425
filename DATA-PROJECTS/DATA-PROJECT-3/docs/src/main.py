import requests
from bs4 import BeautifulSoup
import json
import os
import time
import random

def limpiar_texto(texto):
    return texto.strip().replace('\xa0', ' ')

def extraer_info_completa(url):
    response = requests.get(url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')

    # Título del artículo
    titulo = soup.find('h1').get_text(strip=True)

    # Contenedor principal del contenido
    cuerpo = soup.find("div", {"id": "main"})

    if not cuerpo:
        cuerpo = soup.body

    resultado = {
        "titulo": titulo,
        "contenido": {}
    }

    seccion_actual = "introducción"
    resultado["contenido"][seccion_actual] = []

    for tag in cuerpo.find_all(["h2", "p", "ul", "ol"], recursive=True):
        if tag.name == "h2":
            seccion_actual = limpiar_texto(tag.get_text()).lower()
            resultado["contenido"][seccion_actual] = []
        elif tag.name == "p":
            texto = limpiar_texto(tag.get_text())
            if texto:
                resultado["contenido"][seccion_actual].append(texto)
        elif tag.name in ["ul", "ol"]:
            items = [limpiar_texto(li.get_text()) for li in tag.find_all("li")]
            resultado["contenido"][seccion_actual].extend(items)

    return resultado

# Crear carpeta para guardar los artículos
os.makedirs("articulos", exist_ok=True)

for numero in range(1, 100001):
    numero_str = str(numero).zfill(6)
    url = f"https://medlineplus.gov/spanish/ency/article/{numero_str}.htm"
    
    try:
        data = extraer_info_completa(url)
    except Exception as e:
        print(f"[{numero_str}] Error al procesar: {e}")
        continue

    if not data or data["titulo"].startswith("Lo sentimos"):
        print(f"[{numero_str}] Ignorado: título inválido o página no encontrada.")
        continue

    # Limpieza del título para usar como nombre de archivo seguro
    titulo_limpio = data["titulo"]
    for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        titulo_limpio = titulo_limpio.replace(char, "_")
    titulo_limpio = titulo_limpio.strip()

    ruta_archivo = os.path.join("articulos", f"{titulo_limpio}.json")

    with open(ruta_archivo, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[{numero_str}] Guardado: {titulo_limpio}.json")

    

