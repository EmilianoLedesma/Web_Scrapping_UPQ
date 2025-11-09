#!/usr/bin/env python3
"""
Bot de Telegram para Sistema de Scraping de Calificaciones UPQ.

Comandos disponibles:
- /start - Inicia el bot
- /grades - Obtiene calificaciones actuales
- /check - Verifica nuevas calificaciones
- /stats - Muestra estadísticas
- /help - Muestra ayuda
"""

import os
import sys
import logging
from typing import Optional
from datetime import datetime

# Configurar UTF-8 para Windows (soporte de emojis)
if sys.platform == "win32":
    try:
        if sys.stdout.encoding != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8')
        if sys.stderr.encoding != 'utf-8':
            sys.stderr.reconfigure(encoding='utf-8')
    except:
        os.environ['PYTHONIOENCODING'] = 'utf-8'

try:
    from telegram import Update
    from telegram.ext import (
        Application,
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters
    )
except ImportError:
    print("❌ Error: python-telegram-bot no está instalado")
    print("   Instala con: pip install python-telegram-bot")
    exit(1)

from config.settings import settings
from scraper.fetcher import UPQScraperSession, FetchError
from scraper.parser import UPQGradesParser, ParserError
from scraper.auth import AuthenticationError
from storage.memory import GradesMemory, StorageError


# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class UPQTelegramBot:
    """Bot de Telegram para consultar calificaciones UPQ."""
    
    def __init__(self, token: str):
        """
        Inicializa el bot.
        
        Args:
            token: Token del bot de Telegram.
        """
        self.token = token
        self.memory = GradesMemory()
        self.app = None
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comando /start - Inicia el bot."""
        welcome_message = """
🎓 *Bot de Calificaciones UPQ*

¡Bienvenido! Este bot te permite consultar tus calificaciones del Sistema Integral UPQ.

*💬 Habla naturalmente:*
Puedes escribir cosas como:
• "¿Cuáles son mis calificaciones?"
• "¿Hay algo nuevo?"
• "Muéstrame las estadísticas"

*⌨️ O usa comandos:*
/grades - Obtener calificaciones actuales
/check - Verificar si hay nuevas calificaciones
/stats - Ver estadísticas del sistema
/help - Mostrar ayuda completa

*Nota:* El bot usa las credenciales configuradas en el servidor.
"""
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comando /help - Muestra ayuda."""
        help_text = """
📚 *Ayuda - Bot de Calificaciones UPQ*

*Comandos:*

/start - Inicia el bot
/grades - Obtiene tus calificaciones actuales y las muestra en formato legible
/check - Compara con el último snapshot y detecta cambios
/stats - Muestra estadísticas del historial
/help - Muestra este mensaje

*Cómo funciona:*

1️⃣ El bot se conecta automáticamente al sistema UPQ
2️⃣ Obtiene tus calificaciones actuales
3️⃣ Guarda snapshots para detectar cambios
4️⃣ Te notifica cuando hay calificaciones nuevas

*Privacidad:*
• El bot solo accede a tu información académica
• No comparte datos con terceros
• Las credenciales están seguras en el servidor
"""
        await update.message.reply_text(help_text, parse_mode='Markdown')
        
    async def grades_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comando /grades - Obtiene calificaciones actuales."""
        await update.message.reply_text("📡 Conectando al sistema UPQ...")
        
        try:
            # Validar configuración
            if not settings.validate():
                await update.message.reply_text(
                    "❌ Error: Credenciales no configuradas en el servidor.\n"
                    "Contacta al administrador."
                )
                return
            
            # Crear sesión y autenticar
            with UPQScraperSession() as session:
                # Login
                if not session.login():
                    await update.message.reply_text("❌ Error de autenticación con el sistema UPQ")
                    return
                
                # Obtener HTML de calificaciones
                html = session.get_grades_html()
                
                # Parsear
                parser = UPQGradesParser(html)
                grades = parser.parse_grades()
                
                # Guardar snapshot
                self.memory.add_snapshot(grades)
                self.memory.save()
                
                # Formatear y enviar
                if grades:
                    message = self._format_grades_message(grades)
                    await update.message.reply_text(message, parse_mode='Markdown')
                else:
                    await update.message.reply_text("⚠️ No se encontraron calificaciones")
                    
        except AuthenticationError as e:
            logger.error(f"Authentication error: {e}")
            await update.message.reply_text(f"❌ Error de autenticación: {e}")
            
        except FetchError as e:
            logger.error(f"Fetch error: {e}")
            await update.message.reply_text(f"❌ Error al obtener datos: {e}")
            
        except ParserError as e:
            logger.error(f"Parser error: {e}")
            await update.message.reply_text(
                f"❌ Error al parsear HTML: {e}\n"
                "El formato del sistema puede haber cambiado."
            )
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Error inesperado: {e}")
            
    async def check_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comando /check - Verifica nuevas calificaciones."""
        await update.message.reply_text("🔍 Verificando nuevas calificaciones...")
        
        try:
            # Validar configuración
            if not settings.validate():
                await update.message.reply_text(
                    "❌ Error: Credenciales no configuradas en el servidor.\n"
                    "Contacta al administrador."
                )
                return
            
            # Crear sesión y autenticar
            with UPQScraperSession() as session:
                # Login
                if not session.login():
                    await update.message.reply_text("❌ Error de autenticación con el sistema UPQ")
                    return
                
                # Obtener calificaciones actuales
                html = session.get_grades_html()
                parser = UPQGradesParser(html)
                current_grades = parser.parse_grades()
                
                # Guardar snapshot
                self.memory.add_snapshot(current_grades)
                
                # Detectar cambios
                snapshots = self.memory.data.get("snapshots", [])
                
                if len(snapshots) < 2:
                    await update.message.reply_text(
                        "⚠️ No hay snapshot previo para comparar.\n"
                        "Este es el primer snapshot guardado.\n\n"
                        "✅ Ejecuta /check nuevamente en el futuro para detectar cambios."
                    )
                    self.memory.save()
                    return
                
                # Comparar con el penúltimo snapshot
                changes = self.memory.detect_changes(current_grades)
                self.memory.save()
                
                # Enviar resultados
                if changes:
                    message = f"🔔 *¡Se detectaron {len(changes)} cambios!*\n\n"
                    message += self._format_changes_message(changes)
                    await update.message.reply_text(message, parse_mode='Markdown')
                else:
                    previous_snapshot = snapshots[-2]
                    message = (
                        "✅ *No hay cambios desde la última verificación*\n\n"
                        f"Último check: `{previous_snapshot['timestamp']}`"
                    )
                    await update.message.reply_text(message, parse_mode='Markdown')
                    
        except AuthenticationError as e:
            logger.error(f"Authentication error: {e}")
            await update.message.reply_text(f"❌ Error de autenticación: {e}")
            
        except FetchError as e:
            logger.error(f"Fetch error: {e}")
            await update.message.reply_text(f"❌ Error al obtener datos: {e}")
            
        except ParserError as e:
            logger.error(f"Parser error: {e}")
            await update.message.reply_text(
                f"❌ Error al parsear HTML: {e}\n"
                "El formato del sistema puede haber cambiado."
            )
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Error inesperado: {e}")
            
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comando /stats - Muestra estadísticas."""
        stats = self.memory.get_statistics()
        
        message = "📊 *Estadísticas del Sistema*\n\n"
        message += f"📈 Total de snapshots: `{stats['total_snapshots']}`\n"
        message += f"🔔 Total de cambios detectados: `{stats['total_changes']}`\n"
        message += f"🕐 Última verificación: `{stats['last_check'] or 'Nunca'}`\n"
        message += f"📅 Primer snapshot: `{stats['first_snapshot'] or 'N/A'}`\n"
        
        if stats['total_changes'] > 0:
            message += "\n*Últimos 5 cambios:*\n"
            recent = self.memory.get_recent_changes(5)
            message += self._format_changes_message(recent)
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    def _format_grades_message(self, grades: dict) -> str:
        """
        Formatea las calificaciones para Telegram.
        
        Args:
            grades: Diccionario con calificaciones.
            
        Returns:
            Mensaje formateado en Markdown.
        """
        message = "📚 *CALIFICACIONES*\n\n"
        
        # Información del alumno
        if 'alumno' in grades:
            message += f"👤 *{grades['alumno']}*\n"
        if 'matricula' in grades:
            message += f"🆔 Matrícula: `{grades['matricula']}`\n"
        if 'periodo' in grades:
            message += f"📅 Periodo: `{grades['periodo']}`\n"
        
        message += f"🕐 Consulta: `{grades.get('timestamp', 'N/A')}`\n"
        message += "\n" + "=" * 40 + "\n\n"
        
        # Materias
        materias = grades.get('materias', [])
        
        if not materias:
            message += "⚠️ No se encontraron materias\n"
            return message
        
        for materia in materias:
            message += f"📖 *{materia['nombre']}*\n"
            
            if 'profesor' in materia:
                message += f"👨‍🏫 {materia['profesor']}\n"
            if 'grupo' in materia:
                message += f"🏫 Grupo: `{materia['grupo']}`\n"
            
            # Calificaciones
            cals = materia.get('calificaciones', {})
            if cals:
                cal_str = " | ".join([
                    f"{p}: {v if v is not None else '--'}"
                    for p, v in cals.items()
                ])
                message += f"📊 {cal_str}\n"
            
            message += "\n"
        
        return message
        
    def _format_changes_message(self, changes: list) -> str:
        """
        Formatea los cambios detectados para Telegram.
        
        Args:
            changes: Lista de cambios.
            
        Returns:
            Mensaje formateado en Markdown.
        """
        if not changes:
            return "No hay cambios"
        
        message = ""
        for change in changes:
            message += f"📝 *{change['materia']}*\n"
            message += f"   {change['parcial']}: "
            
            old_val = change['calificacion_anterior']
            new_val = change['calificacion_nueva']
            
            old_str = str(old_val) if old_val is not None else "--"
            new_str = str(new_val) if new_val is not None else "--"
            
            message += f"`{old_str}` → `{new_str}`\n"
            message += f"   🕐 {change['timestamp']}\n\n"
        
        return message
        
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Procesa mensajes de texto con lenguaje natural."""
        text = update.message.text.lower().strip()
        
        # Palabras clave para detectar intención
        grades_keywords = [
            'calificaciones', 'calificación', 'notas', 'nota', 'grades', 'grade',
            'cuánto saqué', 'cuanto saque', 'qué saqué', 'que saque',
            'mis calificaciones', 'ver calificaciones', 'mostrar calificaciones',
            'dame mis calificaciones', 'quiero ver mis calificaciones'
        ]
        
        check_keywords = [
            'nuevas', 'nuevo', 'cambios', 'cambio', 'actualización', 'actualizacion',
            'hay algo nuevo', 'algo nuevo', 'verificar', 'revisar', 'check',
            'hay cambios', 'hubo cambios', 'se actualizó', 'se actualizo'
        ]
        
        stats_keywords = [
            'estadísticas', 'estadisticas', 'stats', 'histórico', 'historico',
            'historial', 'cuántos cambios', 'cuantos cambios', 'resumen'
        ]
        
        help_keywords = [
            'ayuda', 'help', 'qué puedes hacer', 'que puedes hacer',
            'cómo funciona', 'como funciona', 'comandos', 'opciones'
        ]
        
        # Detectar intención
        if any(keyword in text for keyword in grades_keywords):
            await self.grades_command(update, context)
        elif any(keyword in text for keyword in check_keywords):
            await self.check_command(update, context)
        elif any(keyword in text for keyword in stats_keywords):
            await self.stats_command(update, context)
        elif any(keyword in text for keyword in help_keywords):
            await self.help_command(update, context)
        else:
            # Respuesta genérica si no se entiende la intención
            response = (
                "🤔 No estoy seguro de qué necesitas.\n\n"
                "Puedes preguntarme cosas como:\n"
                "• \"¿Cuáles son mis calificaciones?\"\n"
                "• \"¿Hay algo nuevo?\"\n"
                "• \"Muéstrame las estadísticas\"\n"
                "• \"Ayuda\"\n\n"
                "O usa los comandos: /grades, /check, /stats, /help"
            )
            await update.message.reply_text(response)
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Maneja errores globales."""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.message:
            await update.message.reply_text(
                "❌ Ocurrió un error al procesar tu solicitud.\n"
                "Por favor intenta nuevamente."
            )
    
    def run(self) -> None:
        """Inicia el bot."""
        logger.info("Iniciando bot de Telegram...")
        
        # Crear aplicación
        self.app = Application.builder().token(self.token).build()
        
        # Registrar handlers
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("grades", self.grades_command))
        self.app.add_handler(CommandHandler("check", self.check_command))
        self.app.add_handler(CommandHandler("stats", self.stats_command))
        
        # Handler de mensajes de texto (lenguaje natural)
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Handler de errores
        self.app.add_error_handler(self.error_handler)
        
        # Iniciar bot
        logger.info("Bot iniciado. Presiona Ctrl+C para detener.")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Punto de entrada para ejecutar el bot."""
    # Obtener token
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token:
        print("❌ Error: TELEGRAM_BOT_TOKEN no está configurado en .env")
        return
    
    # Validar credenciales UPQ
    if not settings.validate():
        print("❌ Error: Credenciales UPQ no configuradas en .env")
        print("   Configura UPQ_USERNAME y UPQ_PASSWORD")
        return
    
    # Crear y ejecutar bot
    bot = UPQTelegramBot(token)
    bot.run()


if __name__ == "__main__":
    main()
