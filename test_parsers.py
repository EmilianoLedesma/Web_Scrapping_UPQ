#!/usr/bin/env python3
"""Test de parsers con archivos debug reales"""

from scraper.parser import parse_kardex, parse_estancias, parse_servicio_social, parse_student_profile

print("=" * 60)
print("🧪 PROBANDO PARSERS CON ARCHIVOS DEBUG REALES")
print("=" * 60)

# Test 1: Kardex
print("\n1️⃣ PROBANDO KARDEX")
print("-" * 60)
try:
    with open('debug_calificaciones.html', 'r', encoding='utf-8') as f:
        html = f.read()
    kardex = parse_kardex(html)
    print(f"✅ Materias encontradas: {len(kardex)}")
    if kardex:
        print(f"   Primera materia: {kardex[0]['materia']} - Cal: {kardex[0]['calificacion']}")
        print(f"   Última materia: {kardex[-1]['materia']} - Cal: {kardex[-1]['calificacion']}")
    else:
        print("❌ No se encontraron materias en kardex")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Estancias
print("\n2️⃣ PROBANDO ESTANCIAS")
print("-" * 60)
try:
    with open('debug_alumno_info_general.html', 'r', encoding='utf-8') as f:
        html = f.read()
    estancias = parse_estancias(html)
    print(f"✅ Estancias encontradas: {len(estancias)}")
    for i, e in enumerate(estancias, 1):
        print(f"   {i}. {e.get('curso')}")
        print(f"      Empresa: {e.get('empresa')}")
        print(f"      Periodo: {e.get('periodo')}")
        print(f"      Estatus: {e.get('estatus')}")
    if not estancias:
        print("❌ No se encontraron estancias")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Servicio Social
print("\n3️⃣ PROBANDO SERVICIO SOCIAL")
print("-" * 60)
try:
    with open('debug_alumno_info_general.html', 'r', encoding='utf-8') as f:
        html = f.read()
    servicio = parse_servicio_social(html)
    print(f"✅ Datos encontrados: {len(servicio)} campos")
    for key, value in servicio.items():
        print(f"   {key}: {value}")
    if not servicio:
        print("❌ No se encontró info de servicio social")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 4: Perfil
print("\n4️⃣ PROBANDO PERFIL")
print("-" * 60)
try:
    with open('debug_home.html', 'r', encoding='utf-8') as f:
        html = f.read()
    perfil = parse_student_profile(html)
    print(f"✅ Datos encontrados: {len(perfil)} campos")
    for key, value in perfil.items():
        print(f"   {key}: {value}")
    if not perfil:
        print("❌ No se encontró info de perfil")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("🏁 FIN DE PRUEBAS")
print("=" * 60)
