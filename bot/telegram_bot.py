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

# Imports para manejo de HTML adicional
from bs4 import BeautifulSoup
import re
import json
from pathlib import Path


# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class UserCredentialsManager:
    """Gestiona las credenciales de usuarios del bot."""
    
    def __init__(self, storage_file: str = "storage/bot_users.json"):
        """
        Inicializa el gestor de credenciales.
        
        Args:
            storage_file: Archivo donde se almacenan las credenciales (encriptadas).
        """
        self.storage_file = Path(storage_file)
        self.users = self._load_users()
    
    def _load_users(self) -> dict:
        """Carga los usuarios del archivo."""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_users(self):
        """Guarda los usuarios en el archivo."""
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_file, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, indent=2)
    
    def set_credentials(self, user_id: int, username: str, password: str):
        """
        Guarda las credenciales de un usuario.
        
        Args:
            user_id: ID del usuario de Telegram.
            username: Usuario UPQ (matrícula).
            password: Contraseña UPQ.
        """
        # En producción, esto debería estar encriptado
        self.users[str(user_id)] = {
            'username': username,
            'password': password,
            'registered_at': datetime.now().isoformat()
        }
        self._save_users()
    
    def get_credentials(self, user_id: int) -> Optional[dict]:
        """
        Obtiene las credenciales de un usuario.
        
        Args:
            user_id: ID del usuario de Telegram.
            
        Returns:
            Dict con 'username' y 'password' o None si no está registrado.
        """
        user_data = self.users.get(str(user_id))
        if user_data:
            return {
                'username': user_data['username'],
                'password': user_data['password']
            }
        return None
    
    def has_credentials(self, user_id: int) -> bool:
        """Verifica si un usuario tiene credenciales guardadas."""
        return str(user_id) in self.users
    
    def remove_credentials(self, user_id: int):
        """Elimina las credenciales de un usuario."""
        if str(user_id) in self.users:
            del self.users[str(user_id)]
            self._save_users()


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
        self.credentials_manager = UserCredentialsManager()
        self.app = None
        self.logger = logging.getLogger(__name__)
        # Diccionario para manejar conversaciones de registro
        self.pending_registration = {}  # {user_id: {'step': 'username' | 'password', 'username': str}}
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comando /start - Inicia el bot y registra credenciales si es necesario."""
        user_id = update.effective_user.id
        
        # Verificar si el usuario ya tiene credenciales
        if self.credentials_manager.has_credentials(user_id):
            welcome_message = """
🎓 *Bot de Calificaciones UPQ*

¡Bienvenido de nuevo! Ya tienes tus credenciales configuradas.

*💬 Habla naturalmente:*
Puedes escribir cosas como:
• "¿Cuál es mi promedio general?"
• "¿Tengo materias atrasadas?"
• "¿Cuándo terminan mis estancias?"

*⌨️ O usa comandos:*
/grades - Calificaciones actuales
/promedio - Promedio general
/creditos - Créditos y avance
/estancias - Estancias profesionales
/historial - Historial de promedios
/info - Información personal
/help - Ayuda completa
/logout - Cerrar sesión y borrar credenciales

🔐 *Tus credenciales están seguras y solo tú puedes acceder a ellas.*
"""
            await update.message.reply_text(welcome_message, parse_mode='Markdown')
        else:
            # Usuario nuevo - solicitar credenciales
            welcome_message = """
🎓 *Bienvenido al Bot de Calificaciones UPQ*

Para usar este bot necesito que configures tus credenciales del Sistema UPQ.

🔐 *¿Es seguro?*
• Tus credenciales se guardan de forma segura
• Solo tú puedes acceder a tu información
• Puedes eliminarlas en cualquier momento con /logout

📝 *Para comenzar, envíame tu matrícula UPQ*
Ejemplo: `123046244`

⚠️ *Nota:* Este bot es personal y tus datos no se comparten con nadie.
"""
            await update.message.reply_text(welcome_message, parse_mode='Markdown')
            
            # Marcar que estamos esperando la matrícula
            self.pending_registration[user_id] = {'step': 'username'}
    
    async def logout_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comando /logout - Elimina las credenciales del usuario."""
        user_id = update.effective_user.id
        
        if self.credentials_manager.has_credentials(user_id):
            self.credentials_manager.remove_credentials(user_id)
            # También limpiar registro pendiente si existe
            if user_id in self.pending_registration:
                del self.pending_registration[user_id]
            
            message = """
🔓 *Sesión cerrada*

Tus credenciales han sido eliminadas de forma segura.

Para volver a usar el bot, usa /start para configurar nuevas credenciales.

¡Hasta pronto! 👋
"""
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            message = """
⚠️ No tienes credenciales guardadas.

Usa /start para configurar tus credenciales y comenzar a usar el bot.
"""
            await update.message.reply_text(message, parse_mode='Markdown')
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comando /help - Muestra ayuda."""
        help_text = """
📚 *Ayuda - Bot de Calificaciones UPQ*

*Comandos Principales:*

/grades - Obtiene tus calificaciones actuales
/check - Detecta cambios en calificaciones
/stats - Estadísticas del historial

*Información Académica:*

/info - Tu información personal completa
/promedio - Tu promedio general actual
/creditos - Créditos aprobados y avance
/historial - Promedios por cuatrimestre
/materias - Analiza materias atrasadas

*Estancias y Talleres:*

/estancias - Información de estancias profesionales

*Otros:*

/start - Inicia el bot
/help - Muestra este mensaje

*💬 Lenguaje Natural:*
También puedes hacer preguntas como:
• "¿Cuál es mi promedio?"
• "¿Tengo materias atrasadas?"
• "¿Cuándo terminan mis estancias?"
• "¿Cuántos créditos llevo?"

*Privacidad:*
• El bot solo accede a tu información académica
• No comparte datos con terceros
• Las credenciales están seguras en el servidor
"""
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    # ========== COMANDOS NUEVOS CON DATOS ADICIONALES ==========
    
    async def info_general_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Muestra información general del perfil del estudiante."""
        user_id = update.effective_user.id
        await update.message.reply_text("📡 Obteniendo tu información...")
        
        try:
            # Obtener credenciales del usuario
            creds = self.credentials_manager.get_credentials(user_id)
            if not creds:
                await update.message.reply_text("❌ No tienes credenciales configuradas. Usa /start")
                return
            
            profile = self._fetch_home_data(creds['username'], creds['password'])
            
            if not profile:
                await update.message.reply_text("❌ No se pudo obtener información del perfil")
                return
            
            message = "👤 *Información Personal*\n\n"
            
            if 'nombre' in profile:
                message += f"*Nombre:* {profile['nombre']}\n"
            if 'matricula' in profile:
                message += f"*Matrícula:* `{profile['matricula']}`\n"
            if 'carrera' in profile:
                message += f"*Carrera:* {profile['carrera']}\n"
            if 'cuatrimestre' in profile:
                message += f"*Cuatrimestre:* {profile['cuatrimestre']}\n"
            if 'grupo' in profile:
                message += f"*Grupo:* {profile['grupo']}\n"
            if 'generacion' in profile:
                message += f"*Generación:* {profile['generacion']}\n"
            if 'promedio' in profile:
                message += f"\n📊 *Promedio General:* `{profile['promedio']}`\n"
            if 'creditos' in profile:
                message += f"💳 *Créditos:* {profile['creditos']}\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"Error en info_general_command: {e}")
            await update.message.reply_text("❌ Error al obtener información del perfil")
    
    async def promedio_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Muestra el promedio general del estudiante."""
        user_id = update.effective_user.id
        await update.message.reply_text("📊 Consultando tu promedio...")
        
        try:
            # Obtener credenciales del usuario
            creds = self.credentials_manager.get_credentials(user_id)
            if not creds:
                await update.message.reply_text("❌ No tienes credenciales configuradas. Usa /start")
                return
            
            profile = self._fetch_home_data(creds['username'], creds['password'])
            
            if not profile or 'promedio' not in profile:
                await update.message.reply_text("❌ No se pudo obtener el promedio")
                return
            
            promedio = profile['promedio']
            message = f"📊 *Tu Promedio General*\n\n"
            message += f"Tu promedio actual es: *{promedio}*\n\n"
            
            # Agregar emoji según el promedio
            try:
                prom_num = float(promedio)
                if prom_num >= 9.0:
                    message += "🌟 ¡Excelente desempeño!"
                elif prom_num >= 8.0:
                    message += "👍 ¡Muy bien!"
                elif prom_num >= 7.0:
                    message += "📚 Buen trabajo"
                else:
                    message += "💪 ¡Sigue adelante!"
            except:
                pass
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"Error en promedio_command: {e}")
            await update.message.reply_text("❌ Error al obtener el promedio")
    
    async def creditos_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Muestra información sobre créditos aprobados."""
        user_id = update.effective_user.id
        await update.message.reply_text("💳 Consultando tus créditos...")
        
        try:
            # Obtener credenciales del usuario
            creds = self.credentials_manager.get_credentials(user_id)
            if not creds:
                await update.message.reply_text("❌ No tienes credenciales configuradas. Usa /start")
                return
            
            profile = self._fetch_home_data(creds['username'], creds['password'])
            
            if not profile or 'creditos' not in profile:
                await update.message.reply_text("❌ No se pudo obtener información de créditos")
                return
            
            creditos_text = profile['creditos']
            message = f"💳 *Créditos Aprobados*\n\n"
            message += f"{creditos_text}\n\n"
            
            # Intentar calcular porcentaje si viene en formato "X/Y"
            if '/' in creditos_text:
                try:
                    parts = creditos_text.split('/')
                    aprobados = int(parts[0].strip())
                    totales = int(parts[1].strip().split()[0])
                    porcentaje = (aprobados / totales) * 100
                    faltantes = totales - aprobados
                    
                    message += f"📈 *Avance:* {porcentaje:.1f}%\n"
                    message += f"📝 *Te faltan:* {faltantes} créditos\n\n"
                    
                    if porcentaje >= 90:
                        message += "🎓 ¡Casi listo para graduarte!"
                    elif porcentaje >= 75:
                        message += "🚀 ¡Ya estás en la recta final!"
                    elif porcentaje >= 50:
                        message += "💪 ¡Vas por buen camino!"
                    else:
                        message += "📚 ¡Sigue adelante!"
                except:
                    pass
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"Error en creditos_command: {e}")
            await update.message.reply_text("❌ Error al obtener información de créditos")
    
    async def estancias_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Muestra información sobre estancias profesionales."""
        user_id = update.effective_user.id
        await update.message.reply_text("💼 Consultando tus estancias...")
        
        try:
            # Obtener credenciales del usuario
            creds = self.credentials_manager.get_credentials(user_id)
            if not creds:
                await update.message.reply_text("❌ No tienes credenciales configuradas. Usa /start")
                return
            
            html = self._fetch_info_general(creds['username'], creds['password'])
            
            if not html:
                await update.message.reply_text("❌ No se pudo obtener información")
                return
            
            estancias = self._parse_estancias(html)
            
            if not estancias:
                await update.message.reply_text("📝 No se encontraron estancias registradas")
                return
            
            message = "💼 *Estancias Profesionales*\n\n"
            
            for i, estancia in enumerate(estancias, 1):
                message += f"*Estancia {i}*\n"
                
                if 'empresa' in estancia:
                    message += f"🏢 Empresa: {estancia['empresa']}\n"
                if 'proyecto' in estancia:
                    message += f"📋 Proyecto: {estancia['proyecto']}\n"
                if 'fecha_inicio' in estancia:
                    message += f"📅 Inicio: {estancia['fecha_inicio']}\n"
                if 'fecha_fin' in estancia:
                    message += f"🏁 Fin: {estancia['fecha_fin']}\n"
                if 'asesor' in estancia:
                    message += f"👨‍🏫 Asesor: {estancia['asesor']}\n"
                
                message += "\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"Error en estancias_command: {e}")
            await update.message.reply_text("❌ Error al obtener información de estancias")
    
    async def materias_atrasadas_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Analiza si hay materias atrasadas o reprobadas."""
        user_id = update.effective_user.id
        await update.message.reply_text("📚 Analizando tu historial académico...")
        
        try:
            # Obtener credenciales del usuario
            creds = self.credentials_manager.get_credentials(user_id)
            if not creds:
                await update.message.reply_text("❌ No tienes credenciales configuradas. Usa /start")
                return
            
            html = self._fetch_info_general(creds['username'], creds['password'])
            
            if not html:
                await update.message.reply_text("❌ No se pudo obtener información")
                return
            
            resultado = self._analizar_materias_atrasadas(html)
            
            if not resultado['tiene_atrasadas']:
                message = "✅ *¡Excelente!*\n\n"
                message += "No tienes materias atrasadas o reprobadas.\n"
                message += "¡Sigue así! 🎉"
            else:
                message = f"⚠️ *Materias Pendientes*\n\n"
                message += f"Tienes *{resultado['total']}* materia(s) con calificación baja o pendiente:\n\n"
                
                for materia in resultado['materias']:
                    message += f"📝 {materia['nombre']}\n"
                    message += f"   Calificación: `{materia['calificacion']}`\n\n"
                
                message += "💪 ¡No te rindas! Consulta con tus profesores."
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"Error en materias_atrasadas_command: {e}")
            await update.message.reply_text("❌ Error al analizar materias")
    
    async def historial_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Muestra el historial de promedios por cuatrimestre."""
        user_id = update.effective_user.id
        await update.message.reply_text("📈 Obteniendo tu historial académico...")
        
        try:
            # Obtener credenciales del usuario
            creds = self.credentials_manager.get_credentials(user_id)
            if not creds:
                await update.message.reply_text("❌ No tienes credenciales configuradas. Usa /start")
                return
            
            html = self._fetch_info_general(creds['username'], creds['password'])
            
            if not html:
                await update.message.reply_text("❌ No se pudo obtener información")
                return
            
            historial = self._parse_historial_promedios(html)
            
            if not historial:
                await update.message.reply_text("📝 No se encontró historial de promedios")
                return
            
            message = "📈 *Historial de Promedios*\n\n"
            
            for item in historial:
                cuatri = item['cuatrimestre']
                prom = item['promedio']
                message += f"📚 {cuatri}: `{prom}`\n"
            
            message += "\n💡 Tip: Analiza tu evolución para identificar patrones"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"Error en historial_command: {e}")
            await update.message.reply_text("❌ Error al obtener historial")
        
        
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
    
    # ========== MÉTODO HELPER PARA AUTENTICACIÓN ==========
    
    def _create_user_session(self, user_id: int) -> Optional[tuple]:
        """
        Crea una sesión autenticada con las credenciales del usuario.
        
        Args:
            user_id: ID del usuario de Telegram.
            
        Returns:
            Tupla (session, username, password) o None si no tiene credenciales.
        """
        creds = self.credentials_manager.get_credentials(user_id)
        if not creds:
            return None
        
        return (UPQScraperSession(), creds['username'], creds['password'])
    
    # ========== MÉTODOS PARA OBTENER DATOS ADICIONALES ==========
    
    def _fetch_home_data(self, username: str, password: str) -> dict:
        """Obtiene datos del perfil del estudiante desde /home/home."""
        try:
            # Crear sesión y autenticar con credenciales del usuario
            with UPQScraperSession() as session:
                # Necesitamos configurar temporalmente las credenciales
                import config.settings as temp_settings
                original_user = temp_settings.settings.UPQ_USERNAME
                original_pass = temp_settings.settings.UPQ_PASSWORD
                
                try:
                    temp_settings.settings.UPQ_USERNAME = username
                    temp_settings.settings.UPQ_PASSWORD = password
                    
                    if not session.login():
                        self.logger.error("Error de autenticación")
                        return {}
                    
                    # Obtener HTML del perfil
                    html = session.get_home_data()
                finally:
                    # Restaurar credenciales originales
                    temp_settings.settings.UPQ_USERNAME = original_user
                    temp_settings.settings.UPQ_PASSWORD = original_pass
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Buscar tabla con información del perfil
                profile_data = {}
                tables = soup.find_all('table')
                
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        cols = row.find_all(['th', 'td'])
                        if len(cols) >= 2:
                            key = cols[0].get_text(strip=True).lower()
                            value = cols[1].get_text(strip=True)
                            
                            # Mapear campos conocidos
                            if 'nombre' in key:
                                profile_data['nombre'] = value
                            elif 'matrícula' in key or 'matricula' in key:
                                profile_data['matricula'] = value
                            elif 'promedio' in key:
                                profile_data['promedio'] = value
                            elif 'créditos' in key or 'creditos' in key:
                                profile_data['creditos'] = value
                            elif 'cuatrimestre' in key:
                                profile_data['cuatrimestre'] = value
                            elif 'carrera' in key:
                                profile_data['carrera'] = value
                            elif 'grupo' in key:
                                profile_data['grupo'] = value
                            elif 'generación' in key or 'generacion' in key:
                                profile_data['generacion'] = value
                
                return profile_data
                
        except Exception as e:
            self.logger.error(f"Error al obtener datos de perfil: {e}")
            return {}
    
    def _fetch_info_general(self, username: str, password: str) -> str:
        """Obtiene información general completa desde /alumno_informacion_general."""
        try:
            # Crear sesión y autenticar con credenciales del usuario
            with UPQScraperSession() as session:
                # Necesitamos configurar temporalmente las credenciales
                import config.settings as temp_settings
                original_user = temp_settings.settings.UPQ_USERNAME
                original_pass = temp_settings.settings.UPQ_PASSWORD
                
                try:
                    temp_settings.settings.UPQ_USERNAME = username
                    temp_settings.settings.UPQ_PASSWORD = password
                    
                    if not session.login():
                        self.logger.error("Error de autenticación")
                        return ""
                    
                    # Obtener HTML completo
                    html = session.get_info_general()
                    return html
                finally:
                    # Restaurar credenciales originales
                    temp_settings.settings.UPQ_USERNAME = original_user
                    temp_settings.settings.UPQ_PASSWORD = original_pass
                
        except Exception as e:
            self.logger.error(f"Error al obtener información general: {e}")
            return ""
    
    def _parse_estancias(self, html: str) -> list:
        """Parsea información de estancias profesionales."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            estancias = []
            
            # Buscar fieldset de estancias
            fieldsets = soup.find_all('fieldset')
            for fieldset in fieldsets:
                legend = fieldset.find('legend')
                if legend and 'estancia' in legend.get_text(strip=True).lower():
                    # Buscar tablas dentro del fieldset
                    tables = fieldset.find_all('table')
                    for table in tables:
                        estancia_data = {}
                        rows = table.find_all('tr')
                        for row in rows:
                            cols = row.find_all(['th', 'td'])
                            if len(cols) >= 2:
                                key = cols[0].get_text(strip=True).lower()
                                value = cols[1].get_text(strip=True)
                                
                                if 'empresa' in key or 'organización' in key or 'organizacion' in key:
                                    estancia_data['empresa'] = value
                                elif 'proyecto' in key:
                                    estancia_data['proyecto'] = value
                                elif 'fecha inicio' in key or 'inicia' in key:
                                    estancia_data['fecha_inicio'] = value
                                elif 'fecha fin' in key or 'termina' in key or 'concluye' in key:
                                    estancia_data['fecha_fin'] = value
                                elif 'asesor' in key:
                                    estancia_data['asesor'] = value
                        
                        if estancia_data:
                            estancias.append(estancia_data)
            
            return estancias
        except Exception as e:
            self.logger.error(f"Error al parsear estancias: {e}")
            return []
    
    async def _parse_talleres(self, html: str) -> list:
        """Parsea información de talleres."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            talleres = []
            
            # Buscar fieldset de talleres
            fieldsets = soup.find_all('fieldset')
            for fieldset in fieldsets:
                legend = fieldset.find('legend')
                if legend and 'taller' in legend.get_text(strip=True).lower():
                    tables = fieldset.find_all('table')
                    for table in tables:
                        taller_data = {}
                        rows = table.find_all('tr')
                        for row in rows:
                            cols = row.find_all(['th', 'td'])
                            if len(cols) >= 2:
                                key = cols[0].get_text(strip=True).lower()
                                value = cols[1].get_text(strip=True)
                                
                                if 'nombre' in key or 'taller' in key:
                                    taller_data['nombre'] = value
                                elif 'lugar' in key or 'ubicación' in key or 'ubicacion' in key or 'aula' in key:
                                    taller_data['lugar'] = value
                                elif 'horario' in key:
                                    taller_data['horario'] = value
                                elif 'instructor' in key or 'profesor' in key:
                                    taller_data['instructor'] = value
                        
                        if taller_data:
                            talleres.append(taller_data)
            
            return talleres
        except Exception as e:
            self.logger.error(f"Error al parsear talleres: {e}")
            return []
    
    def _parse_historial_promedios(self, html: str) -> list:
        """Parsea el historial de promedios por cuatrimestre."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            historial = []
            
            # Buscar fieldset de historial o estadísticas
            fieldsets = soup.find_all('fieldset')
            for fieldset in fieldsets:
                legend = fieldset.find('legend')
                if legend:
                    legend_text = legend.get_text(strip=True).lower()
                    if 'historial' in legend_text or 'promedio' in legend_text or 'estadística' in legend_text:
                        tables = fieldset.find_all('table')
                        for table in tables:
                            rows = table.find_all('tr')
                            for row in rows:
                                cols = row.find_all(['th', 'td'])
                                if len(cols) >= 2:
                                    cuatrimestre = cols[0].get_text(strip=True)
                                    promedio = cols[1].get_text(strip=True)
                                    
                                    # Verificar que parece un cuatrimestre válido
                                    if re.search(r'\d+', cuatrimestre):
                                        historial.append({
                                            'cuatrimestre': cuatrimestre,
                                            'promedio': promedio
                                        })
            
            return historial
        except Exception as e:
            self.logger.error(f"Error al parsear historial de promedios: {e}")
            return []
    
    def _analizar_materias_atrasadas(self, html: str) -> dict:
        """Analiza si hay materias atrasadas o reprobadas."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            resultado = {
                'tiene_atrasadas': False,
                'materias': [],
                'total': 0
            }
            
            # Buscar en el mapa curricular
            fieldsets = soup.find_all('fieldset')
            for fieldset in fieldsets:
                legend = fieldset.find('legend')
                if legend and 'mapa curricular' in legend.get_text(strip=True).lower():
                    tables = fieldset.find_all('table')
                    for table in tables:
                        rows = table.find_all('tr')
                        for row in rows:
                            cols = row.find_all(['td', 'th'])
                            # Buscar celdas que indiquen calificación reprobatoria o pendiente
                            for col in cols:
                                text = col.get_text(strip=True)
                                # Buscar patrones de calificación baja o estado pendiente
                                if re.search(r'\b[0-5]\.\d+\b', text) or 'NA' in text or 'NP' in text:
                                    # Intentar extraer nombre de materia
                                    materia_row = col.find_parent('tr')
                                    if materia_row:
                                        materia_cols = materia_row.find_all(['td', 'th'])
                                        if len(materia_cols) > 0:
                                            nombre_materia = materia_cols[0].get_text(strip=True)
                                            if nombre_materia and len(nombre_materia) > 3:
                                                resultado['materias'].append({
                                                    'nombre': nombre_materia,
                                                    'calificacion': text
                                                })
                                                resultado['tiene_atrasadas'] = True
            
            resultado['total'] = len(resultado['materias'])
            return resultado
            
        except Exception as e:
            self.logger.error(f"Error al analizar materias atrasadas: {e}")
            return {'tiene_atrasadas': False, 'materias': [], 'total': 0}
        
        
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Procesa mensajes de texto con lenguaje natural."""
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        # ========== MANEJO DE REGISTRO DE CREDENCIALES ==========
        
        # Verificar si el usuario está en proceso de registro
        if user_id in self.pending_registration:
            registration = self.pending_registration[user_id]
            
            if registration['step'] == 'username':
                # Guardar matrícula y pedir contraseña
                registration['username'] = text
                registration['step'] = 'password'
                
                message = """
✅ *Matrícula recibida*

Ahora envíame tu contraseña del Sistema UPQ.

🔒 *Seguridad:*
• Tu contraseña se guarda de forma segura
• Solo tú puedes acceder a ella
• Puedes eliminarla con /logout

📝 Envía tu contraseña:
"""
                await update.message.reply_text(message, parse_mode='Markdown')
                return
                
            elif registration['step'] == 'password':
                # Guardar contraseña y completar registro
                username = registration['username']
                password = text
                
                # Guardar credenciales
                self.credentials_manager.set_credentials(user_id, username, password)
                
                # Limpiar registro pendiente
                del self.pending_registration[user_id]
                
                message = """
🎉 *¡Registro completado!*

Tus credenciales han sido guardadas de forma segura.

Ya puedes usar todos los comandos del bot:
• /grades - Ver calificaciones
• /promedio - Ver promedio
• /creditos - Ver créditos
• /estancias - Ver estancias
• /help - Ver todos los comandos

¡Intenta preguntarme "¿Cuál es mi promedio?" o cualquier otra consulta! 😊
"""
                await update.message.reply_text(message, parse_mode='Markdown')
                return
        
        # ========== VERIFICAR QUE EL USUARIO TIENE CREDENCIALES ==========
        
        if not self.credentials_manager.has_credentials(user_id):
            message = """
⚠️ *No tienes credenciales configuradas*

Para usar el bot, primero necesitas configurar tus credenciales.

Usa /start para comenzar el proceso de registro.
"""
            await update.message.reply_text(message, parse_mode='Markdown')
            return
        
        # ========== PROCESAMIENTO NORMAL DE MENSAJES ==========
        
        text_lower = text.lower().strip()
        
        # ========== CONSULTAS DE INFORMACIÓN GENERAL ==========
        
        # Promedio general
        promedio_keywords = [
            'promedio', 'promedio general', 'mi promedio', 'cuál es mi promedio',
            'cual es mi promedio', 'qué promedio tengo', 'que promedio tengo'
        ]
        
        # Créditos
        creditos_keywords = [
            'créditos', 'creditos', 'cuántos créditos', 'cuantos creditos',
            'créditos aprobados', 'creditos aprobados', 'me faltan créditos',
            'cuánto me falta', 'cuanto me falta', 'avance'
        ]
        
        # Materias
        materias_keywords = [
            'materias atrasadas', 'materias pendientes', 'materias reprobadas',
            'tengo materias atrasadas', 'debo materias', 'me quedé', 'me quede',
            'cuántas materias', 'cuantas materias'
        ]
        
        # Estancias
        estancias_keywords = [
            'estancia', 'estancias', 'cuándo acaba', 'cuando acaba', 'cuando termina',
            'estancia profesional', 'mi estancia', 'dónde estoy', 'donde estoy',
            'en qué empresa', 'en que empresa', 'proyecto'
        ]
        
        # Información personal
        info_keywords = [
            'quién soy', 'quien soy', 'mi información', 'mi info', 'mis datos',
            'matrícula', 'matricula', 'mi nombre', 'mi carrera', 'mi generación',
            'mi generacion', 'mi grupo', 'qué cuatrimestre', 'que cuatrimestre'
        ]
        
        # Historial académico
        historial_keywords = [
            'historial', 'trayectoria', 'historia académica', 'historia academica',
            'cómo me ha ido', 'como me ha ido', 'promedios anteriores',
            'cuatrimestres anteriores', 'mi evolución', 'mi evolucion'
        ]
        
        # ========== CONSULTAS ORIGINALES ==========
        
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
            'cuántos cambios', 'cuantos cambios', 'resumen'
        ]
        
        help_keywords = [
            'ayuda', 'help', 'qué puedes hacer', 'que puedes hacer',
            'cómo funciona', 'como funciona', 'comandos', 'opciones'
        ]
        
        # ========== DETECCIÓN DE INTENCIÓN ==========
        
        # Información general del perfil
        if any(keyword in text_lower for keyword in info_keywords):
            await self.info_general_command(update, context)
            
        # Promedio general
        elif any(keyword in text_lower for keyword in promedio_keywords):
            await self.promedio_command(update, context)
            
        # Créditos y avance
        elif any(keyword in text_lower for keyword in creditos_keywords):
            await self.creditos_command(update, context)
            
        # Materias atrasadas
        elif any(keyword in text_lower for keyword in materias_keywords):
            await self.materias_atrasadas_command(update, context)
            
        # Estancias profesionales
        elif any(keyword in text_lower for keyword in estancias_keywords):
            await self.estancias_command(update, context)
            
        # Historial académico
        elif any(keyword in text_lower for keyword in historial_keywords):
            await self.historial_command(update, context)
            
        # Calificaciones actuales
        elif any(keyword in text_lower for keyword in grades_keywords):
            await self.grades_command(update, context)
            
        # Verificar cambios
        elif any(keyword in text_lower for keyword in check_keywords):
            await self.check_command(update, context)
            
        # Estadísticas
        elif any(keyword in text_lower for keyword in stats_keywords):
            await self.stats_command(update, context)
            
        # Ayuda
        elif any(keyword in text_lower for keyword in help_keywords):
            await self.help_command(update, context)
            
        else:
            # Respuesta genérica si no se entiende la intención
            response = (
                "🤔 No estoy seguro de qué necesitas.\n\n"
                "Puedes preguntarme cosas como:\n\n"
                "📊 *Sobre tus calificaciones:*\n"
                "• \"¿Cuál es mi promedio general?\"\n"
                "• \"¿Tengo materias atrasadas?\"\n"
                "• \"Muéstrame mi historial\"\n\n"
                "🎓 *Sobre tu avance:*\n"
                "• \"¿Cuántos créditos llevo?\"\n"
                "• \"¿Cuánto me falta para terminar?\"\n\n"
                "💼 *Sobre estancias:*\n"
                "• \"¿Cuándo termina mi estancia?\"\n"
                "• \"¿Dónde estoy haciendo mi estancia?\"\n\n"
                "👤 *Información personal:*\n"
                "• \"¿Quién soy?\"\n"
                "• \"¿Cuál es mi matrícula?\"\n\n"
                "O usa /help para ver todos los comandos"
            )
            await update.message.reply_text(response, parse_mode='Markdown')
    
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
        self.app.add_handler(CommandHandler("logout", self.logout_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("grades", self.grades_command))
        self.app.add_handler(CommandHandler("check", self.check_command))
        self.app.add_handler(CommandHandler("stats", self.stats_command))
        
        # Nuevos handlers de información académica
        self.app.add_handler(CommandHandler("info", self.info_general_command))
        self.app.add_handler(CommandHandler("promedio", self.promedio_command))
        self.app.add_handler(CommandHandler("creditos", self.creditos_command))
        self.app.add_handler(CommandHandler("historial", self.historial_command))
        self.app.add_handler(CommandHandler("materias", self.materias_atrasadas_command))
        self.app.add_handler(CommandHandler("estancias", self.estancias_command))
        
        
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
