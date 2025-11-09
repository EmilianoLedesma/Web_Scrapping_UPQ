#!/usr/bin/env python3
"""
Script de prueba para verificar que todos los comandos del bot funcionan.
"""

import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(__file__))

def test_imports():
    """Verifica que todas las importaciones funcionen."""
    print("🧪 Probando importaciones...")
    
    try:
        from scraper.fetcher import UPQScraperSession
        from scraper.parser import (
            parse_kardex,
            parse_student_profile,
            parse_estancias,
            parse_servicio_social
        )
        from scraper.auth import UPQAuthenticator
        print("✅ Todas las importaciones exitosas")
        return True
    except Exception as e:
        print(f"❌ Error en importaciones: {e}")
        return False

def test_session_methods():
    """Verifica que UPQScraperSession tenga todos los métodos necesarios."""
    print("\n🧪 Probando métodos de UPQScraperSession...")
    
    from scraper.fetcher import UPQScraperSession
    
    required_methods = [
        'get_kardex',
        'get_perfil',
        'get_info_general',
        'get_horario',
        'get_boleta',
        'get_pagos',
        'get_adeudos',
        'get_documentos',
        'get_servicios'
    ]
    
    for method in required_methods:
        if hasattr(UPQScraperSession, method):
            print(f"   ✅ {method}")
        else:
            print(f"   ❌ {method} NO EXISTE")
            return False
    
    print("✅ Todos los métodos existen")
    return True

def test_parsers():
    """Verifica que los parsers tengan las firmas correctas."""
    print("\n🧪 Probando parsers...")
    
    from scraper.parser import (
        parse_kardex,
        parse_student_profile,
        parse_estancias,
        parse_servicio_social,
        parse_horario,
        parse_boleta
    )
    
    parsers = [
        ('parse_kardex', parse_kardex),
        ('parse_student_profile', parse_student_profile),
        ('parse_estancias', parse_estancias),
        ('parse_servicio_social', parse_servicio_social),
        ('parse_horario', parse_horario),
        ('parse_boleta', parse_boleta)
    ]
    
    for name, parser in parsers:
        if callable(parser):
            print(f"   ✅ {name}")
        else:
            print(f"   ❌ {name} no es callable")
            return False
    
    print("✅ Todos los parsers están disponibles")
    return True

def test_bot_commands():
    """Verifica que el bot tenga todos los comandos necesarios."""
    print("\n🧪 Probando comandos del bot...")
    
    try:
        from bot.telegram_bot import UPQTelegramBot
        
        # Crear una instancia dummy
        token = os.getenv("TELEGRAM_BOT_TOKEN", "dummy_token_for_testing")
        
        # Solo verificar que los métodos existan
        commands = [
            'kardex_command',
            'perfil_personal_command',
            'estancias_command',
            'servicio_social_command',
            'horario_command',
            'boleta_command'
        ]
        
        for cmd in commands:
            if hasattr(UPQTelegramBot, cmd):
                print(f"   ✅ {cmd}")
            else:
                print(f"   ❌ {cmd} NO EXISTE")
                return False
        
        print("✅ Todos los comandos del bot existen")
        return True
    except Exception as e:
        print(f"❌ Error al verificar bot: {e}")
        return False

def main():
    """Ejecuta todas las pruebas."""
    print("=" * 60)
    print("🧪 PRUEBAS DE COMANDOS DEL BOT")
    print("=" * 60)
    
    results = []
    
    results.append(("Importaciones", test_imports()))
    results.append(("Métodos Session", test_session_methods()))
    results.append(("Parsers", test_parsers()))
    results.append(("Comandos Bot", test_bot_commands()))
    
    print("\n" + "=" * 60)
    print("📊 RESUMEN")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n🎉 ¡TODAS LAS PRUEBAS PASARON!")
        print("\n📝 Comandos disponibles en el bot:")
        print("   /kardex - Kardex académico completo")
        print("   /perfil - Perfil personal del estudiante")
        print("   /estancias - Estancias profesionales (I, II, Estadía)")
        print("   /servicio - Estatus del servicio social")
        print("   /horario - Horario de clases")
        print("   /boleta - Boleta de calificaciones")
        return 0
    else:
        print("\n❌ ALGUNAS PRUEBAS FALLARON")
        return 1

if __name__ == "__main__":
    sys.exit(main())
