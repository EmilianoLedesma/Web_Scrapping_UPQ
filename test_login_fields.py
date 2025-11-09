#!/usr/bin/env python3
"""Script para probar diferentes campos de login."""

import requests
import urllib3
urllib3.disable_warnings()

# Diferentes combinaciones de campos a probar
field_combinations = [
    {'username': '123046244', 'password': 'Emiliano1'},
    {'user': '123046244', 'pass': 'Emiliano1'},
    {'matricula': '123046244', 'password': 'Emiliano1'},
    {'matricula': '123046244', 'contrasena': 'Emiliano1'},
    {'login': '123046244', 'password': 'Emiliano1'},
    {'email': '123046244', 'password': 'Emiliano1'},
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

urls = [
    'https://sistemaintegral.upq.edu.mx/alumnos.php/signin',
    'https://sistemaintegral.upq.edu.mx/alumnos.php',
]

print("=" * 60)
print("Probando diferentes combinaciones de campos de login...")
print("=" * 60)

for url in urls:
    print(f"\n🔍 Probando URL: {url}")
    for i, fields in enumerate(field_combinations, 1):
        print(f"   Intento {i}: {list(fields.keys())}")
        session = requests.Session()
        session.headers.update(headers)

        try:
            response = session.post(
                url,
                data=fields,
                timeout=10,
                verify=False,
                allow_redirects=True
            )

            print(f"      Status: {response.status_code}")
            print(f"      Cookies: {len(session.cookies)}")
            print(f"      URL final: {response.url[:60]}...")

            # Intentar acceder a página de alumno
            test_response = session.get(
                "https://sistemaintegral.upq.edu.mx/alumnos.php",
                timeout=10,
                verify=False
            )
            print(f"      Test acceso: {test_response.status_code}")

            if test_response.status_code == 200:
                print(f"      ✅ POSIBLE COMBINACIÓN CORRECTA!")
                print(f"      Campos: {fields}")
                break

        except Exception as e:
            print(f"      ❌ Error: {str(e)[:50]}")
