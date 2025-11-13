#!/usr/bin/env python3
"""
Explorador profundo del módulo de Desempeño Escolar.
Endpoints: 
  1. /alumnos.php/calificaciones
  2. /alumnos.php/boleta-calificaciones
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper.auth import UPQAuthenticator
from config.settings import settings
import time
from bs4 import BeautifulSoup
import json


def fetch_ajax_endpoint(authenticator: UPQAuthenticator, endpoint: str, name: str) -> str:
    """Obtiene un endpoint AJAX."""
    
    timestamp = int(time.time() * 1000)
    url = f"{settings.UPQ_BASE_URL}{endpoint}?_={timestamp}"
    
    print(f"\n{'='*80}")
    print(f"[INFO] Explorando: {name}")
    print(f"   URL: {url}")
    print('='*80)
    
    # Headers AJAX
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
        
        print(f"[OK] Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type')}")
        print(f"   Tamaño: {len(response.text)} bytes")
        
        return response.text
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return ""


def analyze_html_deep(html: str, name: str) -> dict:
    """Análisis profundo del HTML."""
    
    if not html:
        return {}
    
    soup = BeautifulSoup(html, 'html.parser')
    
    analysis = {
        'name': name,
        'size': len(html),
        'tables': [],
        'forms': [],
        'selects': [],
        'links': [],
        'scripts_count': 0,
        'divs_with_id': [],
        'fieldsets': []
    }
    
    # Analizar tablas
    tables = soup.find_all('table')
    print(f"\n[INFO] Tablas encontradas: {len(tables)}")
    
    for i, table in enumerate(tables):
        table_info = {
            'index': i,
            'id': table.get('id'),
            'class': table.get('class'),
            'headers': [],
            'rows_count': 0,
            'sample_data': []
        }
        
        # Headers
        headers = table.find_all('th')
        table_info['headers'] = [th.get_text(strip=True) for th in headers]
        
        # Filas
        rows = table.find_all('tr')
        table_info['rows_count'] = len(rows)
        
        # Sample data (primeras 5 filas)
        for row in rows[:5]:
            cells = row.find_all(['td', 'th'])
            cell_texts = [c.get_text(strip=True) for c in cells]
            if any(cell_texts):
                table_info['sample_data'].append(cell_texts)
        
        analysis['tables'].append(table_info)
        
        # Imprimir info de tabla
        print(f"\n  [INFO] Tabla {i+1}:")
        if table_info['id']:
            print(f"     ID: {table_info['id']}")
        if table_info['headers']:
            print(f"     Headers: {table_info['headers'][:10]}")
        print(f"     Filas: {table_info['rows_count']}")
        if table_info['sample_data']:
            print(f"     Primeras filas:")
            for row_data in table_info['sample_data'][:3]:
                if len(row_data) <= 10:
                    print(f"       {row_data}")
                else:
                    print(f"       {row_data[:10]}... (total: {len(row_data)} columnas)")
    
    # Analizar formularios
    forms = soup.find_all('form')
    print(f"\n[INFO] Formularios encontrados: {len(forms)}")
    
    for i, form in enumerate(forms):
        form_info = {
            'index': i,
            'id': form.get('id'),
            'action': form.get('action'),
            'method': form.get('method', 'GET'),
            'inputs': []
        }
        
        inputs = form.find_all(['input', 'select', 'textarea'])
        for inp in inputs:
            input_info = {
                'type': inp.name,
                'name': inp.get('name'),
                'id': inp.get('id'),
                'value': inp.get('value')
            }
            form_info['inputs'].append(input_info)
        
        analysis['forms'].append(form_info)
        
        print(f"\n  [INFO] Formulario {i+1}:")
        print(f"     Action: {form_info['action']}")
        print(f"     Method: {form_info['method']}")
        print(f"     Inputs: {len(form_info['inputs'])}")
        for inp in form_info['inputs'][:10]:
            print(f"       - {inp['type']}: {inp['name']} (id={inp['id']})")
    
    # Analizar selects (dropdowns)
    selects = soup.find_all('select')
    print(f"\n[INFO] Selectores (dropdowns): {len(selects)}")
    
    for i, select in enumerate(selects):
        select_info = {
            'name': select.get('name'),
            'id': select.get('id'),
            'options': []
        }
        
        options = select.find_all('option')
        for opt in options:
            select_info['options'].append({
                'value': opt.get('value'),
                'text': opt.get_text(strip=True)
            })
        
        analysis['selects'].append(select_info)
        
        print(f"\n  [INFO] Select {i+1}:")
        print(f"     Name: {select_info['name']}")
        print(f"     ID: {select_info['id']}")
        print(f"     Opciones: {len(select_info['options'])}")
        for opt in select_info['options'][:10]:
            print(f"       - {opt['value']}: {opt['text']}")
    
    # Enlaces interesantes
    links = soup.find_all('a', href=True)
    interesting_links = []
    for link in links:
        href = link.get('href')
        if 'alumnos.php' in href or href.startswith('/'):
            text = link.get_text(strip=True)
            if text:
                interesting_links.append({'href': href, 'text': text})
    
    analysis['links'] = interesting_links[:20]
    print(f"\n[INFO] Enlaces interesantes: {len(interesting_links)}")
    for link in interesting_links[:10]:
        print(f"   - {link['text']}: {link['href']}")
    
    # Scripts
    scripts = soup.find_all('script')
    analysis['scripts_count'] = len(scripts)
    print(f"\n[INFO] Scripts: {len(scripts)}")
    
    # Divs con ID
    divs_with_id = soup.find_all('div', id=True)
    analysis['divs_with_id'] = [{'id': d.get('id'), 'class': d.get('class')} for d in divs_with_id]
    print(f"\n[INFO] Divs con ID: {len(divs_with_id)}")
    for div in divs_with_id[:10]:
        print(f"   - ID: {div.get('id')}, Class: {div.get('class')}")
    
    # Fieldsets
    fieldsets = soup.find_all('fieldset')
    for fs in fieldsets:
        legend = fs.find('legend')
        analysis['fieldsets'].append({
            'legend': legend.get_text(strip=True) if legend else None
        })
    
    if fieldsets:
        print(f"\n[INFO] Fieldsets: {len(fieldsets)}")
        for fs_info in analysis['fieldsets']:
            print(f"   - {fs_info['legend']}")
    
    return analysis


def main():
    """Función principal."""
    print("=" * 80)
    print("[INFO] EXPLORADOR PROFUNDO: DESEMPEÑO ESCOLAR")
    print("=" * 80)
    
    # Autenticar
    print("\n[INFO] Autenticando...")
    authenticator = UPQAuthenticator()
    
    if not authenticator.login():
        print("[ERROR] Error de autenticación")
        return
    
    print("[OK] Autenticación exitosa")
    
    # Endpoints a explorar
    endpoints = [
        {
            'path': '/alumnos.php/calificaciones',
            'name': 'CALIFICACIONES (Desempeño Escolar)',
            'file': 'debug_calificaciones.html'
        },
        {
            'path': '/alumnos.php/boleta-calificaciones',
            'name': 'BOLETA DE CALIFICACIONES',
            'file': 'debug_boleta_calificaciones.html'
        }
    ]
    
    all_analysis = []
    
    for endpoint in endpoints:
        # Fetch
        html = fetch_ajax_endpoint(authenticator, endpoint['path'], endpoint['name'])
        
        if html:
            # Guardar
            with open(endpoint['file'], 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"\n[INFO] Guardado en: {endpoint['file']}")
            
            # Analizar
            analysis = analyze_html_deep(html, endpoint['name'])
            all_analysis.append(analysis)
            
            # Preview
            print(f"\n[INFO] Preview (primeros 600 caracteres):")
            print("-" * 80)
            preview = html[:600].replace('\n', ' ').replace('\r', '')
            print(preview + "...")
            print("-" * 80)
    
    # Guardar análisis completo en JSON
    report = {
        'timestamp': __import__('datetime').datetime.now().isoformat(),
        'endpoints': all_analysis
    }
    
    with open('desempeno_escolar_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 80)
    print("[INFO] RESUMEN FINAL")
    print("=" * 80)
    
    for analysis in all_analysis:
        print(f"\n[INFO] {analysis['name']}")
        print(f"   Tamaño: {analysis['size']} bytes")
        print(f"   Tablas: {len(analysis['tables'])}")
        print(f"   Formularios: {len(analysis['forms'])}")
        print(f"   Selectores: {len(analysis['selects'])}")
        print(f"   Enlaces: {len(analysis['links'])}")
        print(f"   Scripts: {analysis['scripts_count']}")
        print(f"   Divs con ID: {len(analysis['divs_with_id'])}")
        print(f"   Fieldsets: {len(analysis['fieldsets'])}")
    
    print(f"\n[INFO] Reporte técnico completo: desempeno_escolar_report.json")
    print("\n[OK] Exploración profunda completada")
    
    # Cerrar sesión
    authenticator.logout()


if __name__ == "__main__":
    main()
