#!/usr/bin/env python3
"""
Explorador COMPLETO de todos los endpoints del SII.
Basado en EndpointsExplorables.md + endpoints previamente descubiertos.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper.auth import UPQAuthenticator
from config.settings import settings
import time
from bs4 import BeautifulSoup
import json


def fetch_ajax_endpoint(authenticator: UPQAuthenticator, endpoint: str, name: str, params: dict = None) -> tuple:
    """Obtiene un endpoint AJAX y retorna (html, info)."""
    
    timestamp = int(time.time() * 1000)
    
    # Construir URL con parámetros
    if params:
        param_str = '&'.join([f"{k}={v}" for k, v in params.items()])
        url = f"{settings.UPQ_BASE_URL}{endpoint}?{param_str}&_={timestamp}"
    else:
        url = f"{settings.UPQ_BASE_URL}{endpoint}?_={timestamp}"
    
    print(f"\n{'='*80}")
    print(f"[INFO] {name}")
    print(f"   {url}")
    print('=' * 80)
    
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
        
        info = {
            'name': name,
            'url': url,
            'status': response.status_code,
            'content_type': response.headers.get('Content-Type'),
            'size': len(response.text)
        }
        
        print(f"[OK] {response.status_code} | {info['content_type']} | {info['size']} bytes")
        
        return response.text, info
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return "", {'name': name, 'url': url, 'status': 'ERROR', 'error': str(e)}


def analyze_deep(html: str, name: str) -> dict:
    """Análisis profundo y compacto."""
    
    if not html:
        return {'name': name, 'empty': True}
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Tablas
    tables = soup.find_all('table')
    tables_info = []
    
    for i, table in enumerate(tables):
        headers = [th.get_text(strip=True) for th in table.find_all('th')]
        rows = table.find_all('tr')
        
        # Sample de primeras 3 filas
        sample = []
        for row in rows[1:4]:  # Skip header
            cells = [c.get_text(strip=True) for c in row.find_all(['td', 'th'])]
            if any(cells):
                sample.append(cells)
        
        tables_info.append({
            'index': i,
            'id': table.get('id'),
            'headers': headers[:15],  # Limitar a 15
            'rows_count': len(rows),
            'sample': sample
        })
    
    # Formularios
    forms = []
    for form in soup.find_all('form'):
        inputs = []
        for inp in form.find_all(['input', 'select']):
            inputs.append({
                'type': inp.name,
                'name': inp.get('name'),
                'value': inp.get('value')
            })
        
        forms.append({
            'action': form.get('action'),
            'method': form.get('method', 'GET'),
            'inputs': inputs[:10]  # Limitar
        })
    
    # Selects
    selects = []
    for select in soup.find_all('select'):
        options = []
        for opt in select.find_all('option'):
            options.append({
                'value': opt.get('value'),
                'text': opt.get_text(strip=True)
            })
        
        selects.append({
            'name': select.get('name'),
            'id': select.get('id'),
            'options': options[:20]  # Limitar
        })
    
    # Divs importantes
    divs_with_id = [{'id': d.get('id'), 'class': d.get('class')} 
                    for d in soup.find_all('div', id=True)]
    
    # Fieldsets
    fieldsets = []
    for fs in soup.find_all('fieldset'):
        legend = fs.find('legend')
        fieldsets.append(legend.get_text(strip=True) if legend else None)
    
    # Enlaces
    links = []
    for link in soup.find_all('a', href=True)[:30]:
        href = link.get('href')
        text = link.get_text(strip=True)
        if text and ('alumnos.php' in href or href.startswith('/')):
            links.append({'href': href, 'text': text})
    
    return {
        'name': name,
        'size': len(html),
        'tables': tables_info,
        'forms': forms,
        'selects': selects,
        'divs_with_id': divs_with_id[:20],
        'fieldsets': fieldsets,
        'links': links[:20],
        'scripts_count': len(soup.find_all('script'))
    }


def print_analysis(analysis: dict):
    """Imprime análisis de forma legible."""
    
    if analysis.get('empty'):
        print(f"[WARN] {analysis['name']}: SIN CONTENIDO")
        return
    
    print(f"\n[INFO] {analysis['name']}")
    print(f"   Tamaño: {analysis['size']} bytes")
    print(f"   Tablas: {len(analysis.get('tables', []))}")
    print(f"   Formularios: {len(analysis.get('forms', []))}")
    print(f"   Selectores: {len(analysis.get('selects', []))}")
    print(f"   Divs con ID: {len(analysis.get('divs_with_id', []))}")
    
    # Detalles de tablas
    for table in analysis.get('tables', [])[:5]:
        print(f"\n   [INFO] Tabla {table['index'] + 1}: {table['rows_count']} filas")
        if table['headers']:
            print(f"      Headers: {table['headers']}")
        if table['sample']:
            print(f"      Sample:")
            for row in table['sample'][:2]:
                print(f"        {row[:10]}")
    
    # Selectores importantes
    for sel in analysis.get('selects', [])[:3]:
        print(f"\n   [INFO] {sel['name'] or sel['id']}: {len(sel['options'])} opciones")
        for opt in sel['options'][:5]:
            print(f"      - {opt['value']}: {opt['text']}")


def main():
    """Explorador completo."""
    
    print("=" * 80)
    print("[INFO] EXPLORADOR COMPLETO DE ENDPOINTS SII")
    print("=" * 80)
    
    # Autenticar
    print("\n[INFO] Autenticando...")
    authenticator = UPQAuthenticator()
    
    if not authenticator.login():
        print("[ERROR] Error de autenticación")
        return
    
    print("[OK] Autenticación exitosa")
    
    # Todos los endpoints a explorar
    endpoints = [
        # === YA EXPLORADOS (RE-VERIFICAR) ===
        {
            'path': '/alumnos.php/home/home',
            'name': 'HOME - Perfil Principal',
            'file': 'debug_home.html'
        },
        {
            'path': '/alumnos.php/alumno_informacion_general',
            'name': 'INFORMACIÓN GENERAL - Trayectoria Completa',
            'file': 'debug_alumno_info_general.html',
            'params': {'mid': '16746'}
        },
        {
            'path': '/alumnos.php/calificaciones',
            'name': 'CALIFICACIONES - Kárdex Completo',
            'file': 'debug_calificaciones.html'
        },
        {
            'path': '/alumnos.php/boleta-calificaciones',
            'name': 'BOLETA - Calificaciones Detalladas',
            'file': 'debug_boleta_calificaciones.html'
        },
        
        # === NUEVOS ENDPOINTS DEL ARCHIVO MD ===
        {
            'path': '/alumnos.php/pagos',
            'name': 'PAGOS - Historial de Pagos',
            'file': 'debug_pagos_historial.html'
        },
        {
            'path': '/alumnos.php/pagos-en-proceso',
            'name': 'PAGOS EN PROCESO',
            'file': 'debug_pagos_proceso.html'
        },
        {
            'path': '/alumnos.php/controlpagos/pagosEnAdeudos',
            'name': 'PAGOS EN ADEUDO',
            'file': 'debug_pagos_adeudos.html'
        },
        {
            'path': '/alumnos.php/documentos-en-proceso',
            'name': 'DOCUMENTOS EN PROCESO',
            'file': 'debug_documentos_proceso.html'
        },
        {
            'path': '/alumnos.php/inscripcion',
            'name': 'INSCRIPCIÓN - Seguimiento Cuatrimestral',
            'file': 'debug_inscripcion.html'
        },
        {
            'path': '/alumnos.php/carga-academica',
            'name': 'CARGA ACADÉMICA',
            'file': 'debug_carga_academica.html',
            'params': {'iid': '164456'}
        },
        {
            'path': '/alumnos.php/horario-materias',
            'name': 'HORARIO DE MATERIAS',
            'file': 'debug_horario_materias.html',
            'params': {'iid': '164456'}
        },
        {
            'path': '/alumnos.php/seguimiento-cuatrimestral',
            'name': 'SEGUIMIENTO CUATRIMESTRAL',
            'file': 'debug_seguimiento_cuatrimestral.html'
        },
        
        # === ENDPOINTS ADICIONALES (de exploraciones previas) ===
        {
            'path': '/alumnos.php/servicios',
            'name': 'SERVICIOS',
            'file': 'debug_servicios.html'
        },
        {
            'path': '/alumnos.php/historial-academico',
            'name': 'HISTORIAL ACADÉMICO',
            'file': 'debug_historial_academico.html'
        },
    ]
    
    all_analysis = []
    all_info = []
    
    for endpoint in endpoints:
        # Fetch
        params = endpoint.get('params')
        html, info = fetch_ajax_endpoint(
            authenticator, 
            endpoint['path'], 
            endpoint['name'],
            params
        )
        
        all_info.append(info)
        
        if html:
            # Guardar HTML
            with open(endpoint['file'], 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"[INFO] Archivo guardado: {endpoint['file']}")
            
            # Analizar
            analysis = analyze_deep(html, endpoint['name'])
            all_analysis.append(analysis)
            
            # Imprimir análisis
            print_analysis(analysis)
        else:
            all_analysis.append({'name': endpoint['name'], 'empty': True})
        
        # Pausa entre requests
        time.sleep(0.5)
    
    # Guardar reporte JSON completo
    report = {
        'timestamp': __import__('datetime').datetime.now().isoformat(),
        'total_endpoints': len(endpoints),
        'successful': len([i for i in all_info if i.get('status') == 200]),
        'failed': len([i for i in all_info if i.get('status') != 200]),
        'info': all_info,
        'analysis': all_analysis
    }
    
    with open('exploracion_completa_sii.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # Resumen final
    print("\n" + "=" * 80)
    print("[INFO] RESUMEN FINAL DE EXPLORACIÓN COMPLETA")
    print("=" * 80)
    print(f"\n[INFO] Endpoints explorados: {report['total_endpoints']}")
    print(f"[OK] Exitosos: {report['successful']}")
    print(f"[WARN] Fallidos: {report['failed']}")
    
    print("\n[INFO] ENDPOINTS CON DATOS:")
    for analysis in all_analysis:
        if not analysis.get('empty'):
            tables = len(analysis.get('tables', []))
            forms = len(analysis.get('forms', []))
            selects = len(analysis.get('selects', []))
        print(f"\n  {analysis['name']}")
        print(f"    Tablas: {tables} | Formularios: {forms} | Selectores: {selects}")
    
    print(f"\n[INFO] Reporte completo: exploracion_completa_sii.json")
    print("\n[OK] Exploración completa terminada")
    
    authenticator.logout()


if __name__ == "__main__":
    main()
