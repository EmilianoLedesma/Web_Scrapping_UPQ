#!/usr/bin/env python3
"""
Script de inicio para el Bot de Telegram.

Uso:
    python run_bot.py
"""

import sys
import os

# Configurar UTF-8 para Windows (soporte de emojis)
if sys.platform == "win32":
    try:
        if sys.stdout.encoding != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8')
        if sys.stderr.encoding != 'utf-8':
            sys.stderr.reconfigure(encoding='utf-8')
    except:
        os.environ['PYTHONIOENCODING'] = 'utf-8'

# Asegurar que el directorio actual esté en el path
sys.path.insert(0, os.path.dirname(__file__))

# Importar y ejecutar el bot
from bot.telegram_bot import main

if __name__ == "__main__":
    print("=" * 60)
    print("  Bot de Telegram - Sistema de Calificaciones UPQ")
    print("=" * 60)
    print()
    
    main()
