#!/usr/bin/env python3
"""
Explorador específico del endpoint de información general del alumno.
Endpoint: /alumnos.php/alumno_informacion_general
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper.auth import UPQAuthenticator
from config.settings import settings
import time


def fetch_student_general_info(authenticator: UPQAuthenticator) -> str:
    """Obtiene la información general del alumno (trayectoria escolar)."""
    
    # Timestamp en milisegundos (como en la petición AJAX)
    timestamp = int(time.time() * 1000)
    
    # mid parece ser un identificador de módulo
    mid = "16746"
    
    url = f"{settings.UPQ_BASE_URL}/alumnos.php/alumno_informacion_general?mid={mid}&_={timestamp}"
    
    print("[INFO] Obteniendo información general del alumno...")
    print(f"   URL: {url}")
    
    # Headers AJAX como los que mostraste
    ajax_headers = {
        'Accept': '*/*',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': f'{settings.UPQ_BASE_URL}/alumnos.php/home/home',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
    }
    
    try:
        response = authenticator.session.get(
            url,
            headers=ajax_headers,
            timeout=settings.REQUEST_TIMEOUT,
            verify=settings.VERIFY_SSL
        )
        
        response.raise_for_status()
        
        print(f"[OK] Respuesta recibida: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type')}")
        print(f"   Tamaño: {len(response.text)} bytes")
        
        return response.text
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return ""


def main():
    """Función principal."""
    print("=" * 80)
    print("[INFO] EXPLORADOR DE INFORMACIÓN GENERAL DEL ALUMNO")
    print("=" * 80)
    
    # Autenticar
    print("\n[INFO] Autenticando...")
    authenticator = UPQAuthenticator()
    
    if not authenticator.login():
        print("[ERROR] Error de autenticación")
        return
    
    print("[OK] Autenticación exitosa\n")
    
    # Obtener información general
    html = fetch_student_general_info(authenticator)
    
    if html:
        # Guardar para análisis
        filename = "debug_alumno_info_general.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"\n[INFO] HTML guardado en: {filename}")
        print(f"   Tamaño del archivo: {len(html)} bytes")
        
        # Análisis rápido del contenido
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Buscar tablas
        tables = soup.find_all('table')
        print(f"\n[INFO] Análisis del contenido:")
        print(f"   Tablas encontradas: {len(tables)}")
        
        # Buscar títulos
        for tag in ['h1', 'h2', 'h3', 'h4']:
            headers = soup.find_all(tag)
            if headers:
                print(f"   [INFO] <{tag}> encontrados: {len(headers)}")
                for h in headers[:3]:
                    print(f"      - {h.get_text(strip=True)}")
        
        # Buscar fieldsets (secciones agrupadas)
        fieldsets = soup.find_all('fieldset')
        if fieldsets:
            print(f"   [INFO] Fieldsets (secciones): {len(fieldsets)}")
            for fs in fieldsets:
                legend = fs.find('legend')
                if legend:
                    print(f"      - {legend.get_text(strip=True)}")
        
        # Analizar tablas
        for i, table in enumerate(tables):
            print(f"\n   [INFO] Tabla {i+1}:")
            headers = table.find_all('th')
            if headers:
                header_texts = [th.get_text(strip=True) for th in headers[:10]]
                print(f"      Headers: {header_texts}")
            
            rows = table.find_all('tr')
            print(f"      Filas: {len(rows)}")
            
            # Mostrar primera fila de datos
            for row in rows[:3]:
                cells = row.find_all(['td', 'th'])
                if cells:
                    cell_texts = [c.get_text(strip=True) for c in cells[:5]]
                    if any(cell_texts):
                        print(f"         {cell_texts}")
        
        # Mostrar preview del HTML
        print(f"\n[INFO] Preview del HTML (primeros 500 caracteres):")
        print("-" * 80)
        preview = html[:500].replace('\n', ' ').replace('\r', '')
        print(preview + "...")
        print("-" * 80)
    
    # Cerrar sesión
    authenticator.logout()
    print("\n[OK] Exploración completada")


if __name__ == "__main__":
    main()
