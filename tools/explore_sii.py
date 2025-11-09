#!/usr/bin/env python3
"""
Explorador del Sistema Integral de Información UPQ.
Navega el sitio autenticado para descubrir endpoints y funcionalidades.
"""

import sys
from pathlib import Path

# Añadir el directorio raíz al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper.auth import UPQAuthenticator
from scraper.fetcher import UPQFetcher
from bs4 import BeautifulSoup
import re
import json


def explore_main_menu(html: str) -> dict:
    """Extrae el menú principal y opciones disponibles."""
    soup = BeautifulSoup(html, 'html.parser')
    
    menu_items = []
    
    # Buscar enlaces en el menú
    for link in soup.find_all('a', href=True):
        href = link.get('href', '')
        text = link.get_text(strip=True)
        
        # Filtrar enlaces del sistema (no externos)
        if href and ('alumnos.php' in href or href.startswith('/')):
            if text and len(text) > 2:
                menu_items.append({
                    'text': text,
                    'href': href,
                    'title': link.get('title', '')
                })
    
    return {
        'menu_items': menu_items,
        'total_links': len(menu_items)
    }


def explore_iframe_content(fetcher: UPQFetcher, iframe_src: str) -> dict:
    """Explora el contenido de un iframe."""
    try:
        from config.settings import settings
        
        # Construir URL completa
        if iframe_src.startswith('/'):
            url = settings.UPQ_BASE_URL + iframe_src
        else:
            url = iframe_src
        
        print(f"  📥 Explorando iframe: {url}")
        
        response = fetcher.session.get(
            url,
            timeout=settings.REQUEST_TIMEOUT,
            verify=settings.VERIFY_SSL
        )
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar enlaces interesantes
            links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                text = link.get_text(strip=True)
                if text and 'alumnos.php' in href:
                    links.append({'text': text, 'href': href})
            
            # Buscar formularios
            forms = []
            for form in soup.find_all('form'):
                action = form.get('action', '')
                method = form.get('method', 'GET')
                inputs = [inp.get('name', '') for inp in form.find_all('input') if inp.get('name')]
                forms.append({
                    'action': action,
                    'method': method,
                    'inputs': inputs
                })
            
            return {
                'status': 'success',
                'links': links[:10],  # Primeros 10
                'forms': forms,
                'html_size': len(response.text)
            }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
    
    return {'status': 'error', 'error': 'Unknown error'}


def explore_endpoints(fetcher: UPQFetcher) -> dict:
    """Explora endpoints conocidos del sistema."""
    from config.settings import settings
    
    endpoints = {
        'inscripciones': '/alumnos.php/inscripcion',
        'home': '/alumnos.php/home/home',
        'perfil': '/alumnos.php/perfil',
        'horario': '/alumnos.php/horario',
        'kardex': '/alumnos.php/kardex',
        'pagos': '/alumnos.php/pagos',
        'adeudos': '/alumnos.php/adeudos',
        'biblioteca': '/alumnos.php/biblioteca',
        'servicios': '/alumnos.php/servicios',
        'documentos': '/alumnos.php/documentos',
        'calendario': '/alumnos.php/calendario',
    }
    
    results = {}
    
    for name, path in endpoints.items():
        url = settings.UPQ_BASE_URL + path
        print(f"\n🔍 Probando endpoint: {name}")
        print(f"   URL: {url}")
        
        try:
            response = fetcher.session.get(
                url,
                timeout=settings.REQUEST_TIMEOUT,
                verify=settings.VERIFY_SSL
            )
            
            status = response.status_code
            content_type = response.headers.get('Content-Type', '')
            size = len(response.text)
            
            # Analizar contenido si es HTML
            info = {
                'status_code': status,
                'content_type': content_type,
                'size': size,
                'available': status == 200,
                'url_final': response.url
            }
            
            if status == 200 and 'html' in content_type:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Buscar títulos
                title = soup.find('title')
                h1 = soup.find('h1')
                h2 = soup.find('h2')
                h3 = soup.find('h3')
                h4 = soup.find('h4')
                
                info['title'] = title.get_text(strip=True) if title else None
                info['heading'] = (
                    h1.get_text(strip=True) if h1 else
                    h2.get_text(strip=True) if h2 else
                    h3.get_text(strip=True) if h3 else
                    h4.get_text(strip=True) if h4 else
                    None
                )
                
                # Buscar tablas
                tables = soup.find_all('table')
                info['tables_count'] = len(tables)
                
                # Buscar formularios
                forms = soup.find_all('form')
                info['forms_count'] = len(forms)
                
                # Guardar HTML si es interesante
                if tables or forms or 'kardex' in name or 'horario' in name:
                    debug_file = f"debug_{name}.html"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    info['saved_to'] = debug_file
                    print(f"   💾 Guardado en: {debug_file}")
            
            results[name] = info
            print(f"   ✅ Status: {status}, Tamaño: {size} bytes")
            
        except Exception as e:
            results[name] = {
                'status_code': None,
                'available': False,
                'error': str(e)
            }
            print(f"   ❌ Error: {e}")
    
    return results


def main():
    """Función principal del explorador."""
    print("=" * 80)
    print("🔍 EXPLORADOR DEL SISTEMA INTEGRAL UPQ")
    print("=" * 80)
    
    # Autenticar
    print("\n🔐 Autenticando...")
    authenticator = UPQAuthenticator()
    
    if not authenticator.login():
        print("❌ Error de autenticación")
        return
    
    print("✅ Autenticación exitosa")
    
    # Crear fetcher
    fetcher = UPQFetcher(authenticator)
    
    # Explorar página principal
    print("\n📄 Explorando página principal del alumno...")
    student_html = fetcher.fetch_student_info()
    
    # Guardar para análisis
    with open('debug_main_page.html', 'w', encoding='utf-8') as f:
        f.write(student_html)
    print("   💾 Guardado en: debug_main_page.html")
    
    # Analizar menú
    menu_info = explore_main_menu(student_html)
    print(f"\n📋 Menú principal: {menu_info['total_links']} enlaces encontrados")
    for item in menu_info['menu_items'][:15]:
        print(f"   - {item['text']}: {item['href']}")
    
    # Explorar iframe si existe
    soup = BeautifulSoup(student_html, 'html.parser')
    iframe = soup.find('iframe', id='main-frame') or soup.find('iframe')
    if iframe and iframe.get('src'):
        print(f"\n🖼️  Iframe principal detectado: {iframe.get('src')}")
        iframe_info = explore_iframe_content(fetcher, iframe.get('src'))
        print(f"   Status: {iframe_info.get('status')}")
        if iframe_info.get('links'):
            print("   Enlaces en iframe:")
            for link in iframe_info['links'][:10]:
                print(f"     - {link['text']}: {link['href']}")
    
    # Explorar endpoints conocidos
    print("\n🌐 Explorando endpoints conocidos del sistema...")
    endpoints_info = explore_endpoints(fetcher)
    
    # Resumen final
    print("\n" + "=" * 80)
    print("📊 RESUMEN DE EXPLORACIÓN")
    print("=" * 80)
    
    available_endpoints = {k: v for k, v in endpoints_info.items() if v.get('available')}
    print(f"\n✅ Endpoints disponibles: {len(available_endpoints)}/{len(endpoints_info)}")
    
    for name, info in available_endpoints.items():
        print(f"\n🔹 {name.upper()}")
        print(f"   URL: {info.get('url_final', 'N/A')}")
        if info.get('heading'):
            print(f"   Título: {info['heading']}")
        if info.get('tables_count'):
            print(f"   Tablas: {info['tables_count']}")
        if info.get('forms_count'):
            print(f"   Formularios: {info['forms_count']}")
        if info.get('saved_to'):
            print(f"   💾 Archivo: {info['saved_to']}")
    
    # Guardar reporte JSON
    report = {
        'timestamp': __import__('datetime').datetime.now().isoformat(),
        'menu': menu_info,
        'endpoints': endpoints_info
    }
    
    with open('exploration_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print("\n💾 Reporte completo guardado en: exploration_report.json")
    print("\n✅ Exploración completada")
    
    # Cerrar sesión
    authenticator.logout()


if __name__ == "__main__":
    main()
