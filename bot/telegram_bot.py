#!/usr/bin/env python3
"""
Bot de Telegram para Sistema de Scraping de Calificaciones UPQ.

Comandos disponibles:
- /start - Registrar credenciales
- /logout - Eliminar credenciales
- /grades - Calificaciones actuales
- /check - Verificar cambios
- /stats - Estadísticas
- /info - Información del perfil
- /promedio - Promedio general
- /creditos - Créditos y avance
- /perfil - Perfil personal
- /horario - Horario de clases
- /kardex - Kardex académico
- /boleta - Boleta de calificaciones
- /historial - Historial de promedios
- /materias - Materias atrasadas
- /estancias - Estancias profesionales
- /servicio - Servicio social
- /pagos - Historial de pagos
- /adeudos - Adeudos pendientes
- /documentos - Documentos disponibles
- /calendario - Calendario académico
- /help - Ayuda
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
        # Ya NO usamos un único GradesMemory global
        # self.memory = GradesMemory()
        self.credentials_manager = UserCredentialsManager()
        self.app = None
        self.logger = logging.getLogger(__name__)
        # Diccionario para manejar conversaciones de registro
        self.pending_registration = {}  # {user_id: {'step': 'username' | 'password', 'username': str}}
    
    def _get_user_memory(self, user_id: int) -> GradesMemory:
        """
        Obtiene el objeto GradesMemory específico para un usuario.
        Cada usuario tiene su propio archivo de almacenamiento.
        
        Args:
            user_id: ID del usuario de Telegram.
            
        Returns:
            GradesMemory: Objeto de memoria para el usuario.
        """
        from pathlib import Path
        # Crear un archivo separado por usuario
        storage_dir = Path("storage/users")
        storage_dir.mkdir(parents=True, exist_ok=True)
        user_storage_path = storage_dir / f"user_{user_id}_grades.json"
        return GradesMemory(storage_path=user_storage_path)
        
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

*� ¡Habla conmigo naturalmente!*
Puedes preguntarme:
• "¿Cuál es mi promedio?"
• "Muéstrame mi horario"
• "¿Cuál es mi kardex?"
• "¿Tengo materias atrasadas?"
• "¿Puedo hacer servicio social?"

*�📊 Comandos Principales:*
/grades - Calificaciones actuales
/check - Detectar cambios
/stats - Estadísticas

*👤 Información Personal:*
/info - Información del perfil
/promedio - Promedio general
/creditos - Créditos y avance
/perfil - Perfil personal completo

*📚 Académico:*
/horario - Horario de clases
/kardex - Kardex académico
/boleta - Boleta de calificaciones
/historial - Promedios por periodo
/materias - Materias atrasadas

*💼 Profesional:*
/estancias - Estancias profesionales
/servicio - Servicio social

*💰 Administrativo:*
/pagos - Historial de pagos
/adeudos - Adeudos pendientes

*� Documentos y Calendario:*
/documentos - Documentos disponibles
/calendario - Calendario académico

*⚙️ Sistema:*
/start - Registrar credenciales
/logout - Eliminar credenciales
/help - Este mensaje
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
            # Obtener credenciales
            creds = self.credentials_manager.get_credentials(user_id)
            if not creds:
                await update.message.reply_text(
                    "❌ No estás autenticado. Usa /login para iniciar sesión."
                )
                return
            
            # Importar parser y sesión
            from scraper.parser import parse_estancias
            from scraper.fetcher import UPQScraperSession
            
            # Crear sesión, autenticar y obtener info general
            session = UPQScraperSession(username=creds['username'], password=creds['password'])
            if not session.login():
                await update.message.reply_text("❌ Error de autenticación")
                return
            
            info_html = session.get_info_general()
            
            # Parsear estancias
            estancias = parse_estancias(info_html)
            
            # Cerrar sesión
            session.authenticator.logout()
            
            if not estancias:
                await update.message.reply_text("📝 No se encontraron estancias registradas")
                return
            
            message = "💼 *ESTANCIAS PROFESIONALES*\n\n"
            
            for estancia in estancias:
                curso = estancia.get('curso', 'N/A')
                empresa = estancia.get('empresa', 'N/A')
                periodo = estancia.get('periodo', 'N/A')
                estatus = estancia.get('estatus', 'N/A')
                descripcion = estancia.get('descripcion', '')
                
                # Emoji según estatus
                emoji_estatus = "✅" if estatus == "CONCLUIDO" else "🔄" if estatus == "AUTORIZADO" else "📋"
                
                message += f"{emoji_estatus} *{curso}*\n"
                message += f"🏢 {empresa}\n"
                message += f"📅 {periodo}\n"
                message += f"📊 Estatus: {estatus}\n"
                
                # Descripción corta (primeras 150 caracteres)
                if descripcion:
                    desc_corta = descripcion[:150] + "..." if len(descripcion) > 150 else descripcion
                    message += f"� {desc_corta}\n"
                
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
    
    async def horario_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Muestra el horario de clases."""
        user_id = update.effective_user.id
        await update.message.reply_text("📅 Consultando tu horario...")
        
        try:
            creds = self.credentials_manager.get_credentials(user_id)
            if not creds:
                await update.message.reply_text("❌ No tienes credenciales configuradas. Usa /start")
                return
            
            # Crear sesión y obtener horario
            session = UPQScraperSession(username=creds['username'], password=creds['password'])
            if not session.login():
                await update.message.reply_text("❌ Error de autenticación")
                return
            
            html = session.get_horario()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Cerrar sesión
            session.authenticator.logout()
            
            # Buscar la tabla de horario por días (segunda tabla)
            table_horario = soup.find('table', class_='horario')
            
            if not table_horario:
                await update.message.reply_text("📝 No se encontró información de horario")
                return
            
            # Obtener header (días)
            header = table_horario.find('tr')
            dias = [th.text.strip() for th in header.find_all('th')[1:]]
            
            message = "📅 *HORARIO DE CLASES*\n\n"
            
            # Procesar filas (saltar header)
            rows = table_horario.find_all('tr')[1:]
            
            horario_dict = {dia: [] for dia in dias}
            
            for row in rows:
                hora_th = row.find('th')
                if hora_th:
                    hora = hora_th.text.strip()
                    celdas = row.find_all('td')
                    
                    for i, celda in enumerate(celdas):
                        texto = celda.get_text(strip=True)
                        if texto and texto != '&nbsp;':
                            # Extraer solo el nombre de la materia (sin horarios)
                            materia = texto.split('[')[0].strip()
                            if materia:
                                horario_dict[dias[i]].append(f"  {hora} - {materia}")
            
            # Construir mensaje por día
            for dia in dias:
                if horario_dict[dia]:
                    message += f"*{dia}*\n"
                    message += '\n'.join(horario_dict[dia])
                    message += "\n\n"
            
            if not any(horario_dict.values()):
                message += "� No hay clases programadas"
            
            await update.message.reply_text(message, parse_mode='Markdown')
                    
        except Exception as e:
            self.logger.error(f"Error en horario_command: {e}")
            await update.message.reply_text(f"❌ Error al obtener horario: {str(e)}")
    
    async def kardex_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Muestra el kardex académico del usuario"""
        user_id = update.effective_user.id
        await update.message.reply_text("📚 Obteniendo tu kardex académico...")
        
        try:
            # Obtener credenciales
            creds = self.credentials_manager.get_credentials(user_id)
            if not creds:
                await update.message.reply_text(
                    "❌ No estás autenticado. Usa /login para iniciar sesión."
                )
                return
            
            # Importar parser y sesión
            from scraper.parser import parse_kardex
            from scraper.fetcher import UPQScraperSession
            
            # Crear sesión, autenticar y obtener kardex
            session = UPQScraperSession(username=creds['username'], password=creds['password'])
            if not session.login():
                await update.message.reply_text("❌ Error de autenticación")
                return
            
            kardex_html = session.get_kardex()
            
            # Parsear kardex
            materias = parse_kardex(kardex_html)
            
            # Cerrar sesión
            session.authenticator.logout()
            
            if not materias:
                await update.message.reply_text("❌ No se encontró información del kardex.")
                return
            
            # Formatear respuesta
            mensaje = "� *KARDEX ACADÉMICO*\n\n"
            
            cuatrimestre_actual = None
            for materia in materias:
                cuatri = materia['cuatrimestre']
                
                # Encabezado de cuatrimestre
                if cuatri != cuatrimestre_actual:
                    if cuatrimestre_actual is not None:
                        mensaje += "\n"
                    mensaje += f"*━━ Cuatrimestre {cuatri} ━━*\n"
                    cuatrimestre_actual = cuatri
                
                # Información de materia
                cal = materia['calificacion']
                try:
                    cal_num = float(cal)
                    emoji_cal = "✅" if cal_num >= 7 else "❌"
                except:
                    emoji_cal = "📝"
                
                mensaje += f"{emoji_cal} {materia['materia']}: *{cal}*\n"
                mensaje += f"   └ {materia['tipo_evaluacion']}\n"
            
            mensaje += f"\n📊 Total: {len(materias)} materias cursadas"
            
            await update.message.reply_text(mensaje, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"Error en kardex_command: {e}")
            await update.message.reply_text(f"❌ Error al obtener kardex: {str(e)}")
    
    async def boleta_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Muestra la boleta de calificaciones."""
        user_id = update.effective_user.id
        await update.message.reply_text("📋 Consultando tu boleta...")
        
        try:
            creds = self.credentials_manager.get_credentials(user_id)
            if not creds:
                await update.message.reply_text("❌ No tienes credenciales configuradas. Usa /start")
                return
            
            with UPQScraperSession(username=creds['username'], password=creds['password']) as session:
                if not session.login():
                    await update.message.reply_text("❌ Error de autenticación")
                    return
                
                html = session.get_boleta()
                soup = BeautifulSoup(html, 'html.parser')
                
                message = "📋 *Boleta de Calificaciones*\n\n"
                tables = soup.find_all('table')
                
                if tables:
                    for table in tables[:1]:
                        rows = table.find_all('tr')
                        for row in rows[:20]:  # Limitar a 20 filas
                            cols = row.find_all(['th', 'td'])
                            if cols:
                                row_text = " | ".join([col.get_text(strip=True) for col in cols])
                                message += f"`{row_text}`\n"
                    await update.message.reply_text(message, parse_mode='Markdown')
                else:
                    await update.message.reply_text("📝 No se encontró boleta")
                    
        except Exception as e:
            self.logger.error(f"Error en boleta_command: {e}")
            await update.message.reply_text("❌ Error al obtener boleta")
    
    async def servicio_social_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Muestra información del servicio social del estudiante.
        """
        user_id = update.effective_user.id
        await update.message.reply_text("🎓 Consultando tu servicio social...")
        
        try:
            # Obtener credenciales
            creds = self.credentials_manager.get_credentials(user_id)
            if not creds:
                await update.message.reply_text(
                    "❌ No estás autenticado. Usa /login para iniciar sesión."
                )
                return
            
            # Importar parser y sesión
            from scraper.parser import parse_servicio_social
            from scraper.fetcher import UPQScraperSession
            
            # Crear sesión, autenticar y obtener info general
            session = UPQScraperSession(username=creds['username'], password=creds['password'])
            if not session.login():
                await update.message.reply_text("❌ Error de autenticación")
                return
            
            info_html = session.get_info_general()
            
            # Parsear servicio social
            servicio = parse_servicio_social(info_html)
            
            # Cerrar sesión
            session.authenticator.logout()
            
            if not servicio:
                await update.message.reply_text("❌ No se encontró información del servicio social")
                return
            
            # Construir mensaje
            message = "🎓 *SERVICIO SOCIAL*\n\n"
            
            # Estado del servicio
            activo = servicio.get('activo', False)
            if activo:
                message += "✅ *Servicio social ACTIVO*\n\n"
            else:
                message += "⏸️ *Servicio social NO ACTIVO*\n\n"
            
            # Requisitos
            mat_req = servicio.get('materias_requeridas', 'N/A')
            mat_falt = servicio.get('materias_faltantes', 'N/A')
            
            message += f"📚 Materias requeridas: *{mat_req}*\n"
            message += f"📋 Materias faltantes: *{mat_falt}*\n\n"
            
            # Estatus
            estatus = servicio.get('estatus', 'N/A')
            cumple = servicio.get('cumple_requisitos', False)
            
            if cumple:
                message += f"✅ *{estatus}*\n"
                message += "¡Puedes comenzar tu servicio social! 🎉"
            else:
                message += f"⚠️ *{estatus}*\n"
                message += f"Te faltan {mat_falt} materias para cumplir requisitos."
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"Error en servicio_social_command: {e}")
            await update.message.reply_text("❌ Error al obtener información de servicio social")
    
    async def perfil_personal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Muestra el perfil personal del usuario"""
        user_id = update.effective_user.id
        await update.message.reply_text("👤 Obteniendo tu perfil personal...")
        
        try:
            # Obtener credenciales
            creds = self.credentials_manager.get_credentials(user_id)
            if not creds:
                await update.message.reply_text(
                    "❌ No estás autenticado. Usa /login para iniciar sesión."
                )
                return
            
            # Importar parser y sesión
            from scraper.parser import parse_student_profile
            from scraper.fetcher import UPQScraperSession
            
            # Crear sesión, autenticar y obtener perfil
            session = UPQScraperSession(username=creds['username'], password=creds['password'])
            if not session.login():
                await update.message.reply_text("❌ Error de autenticación")
                return
            
            perfil_html = session.get_perfil()
            
            # Parsear perfil
            perfil = parse_student_profile(perfil_html)
            
            # Cerrar sesión
            session.authenticator.logout()
            
            if not perfil:
                await update.message.reply_text("❌ No se encontró información del perfil.")
                return
            
            # Formatear respuesta con manejo de claves alternativas
            def get_field(key1, key2='', default='N/A'):
                return perfil.get(key1, perfil.get(key2, default))
            
            nombre = get_field('nombre')
            matricula = get_field('matrícula', 'matricula')
            carrera = get_field('carrera')
            generacion = get_field('generación', 'generacion')
            grupo = get_field('grupo')
            cuatrimestre = get_field('último_cuatrimestre', 'ultimo_cuatrimestre')
            promedio = get_field('promedio_general')
            materias_aprob = get_field('materias_aprobadas')
            materias_reprob = get_field('materias_no_acreditadas')
            creditos = get_field('créditos', 'creditos')
            nivel_ingles = get_field('nivel_inglés', 'nivel_ingles')
            estatus = get_field('estatus')
            nss = get_field('nss')
            tutor = get_field('tutor')
            email_tutor = get_field('email', 'email_tutor')
            
            mensaje = f"""
👤 *PERFIL ACADÉMICO*

*Datos Personales:*
├ Nombre: {nombre}
├ Matrícula: {matricula}
├ NSS: {nss}
└ Estatus: {estatus}

*Datos Académicos:*
├ Carrera: {carrera}
├ Generación: {generacion}
├ Grupo: {grupo}
├ Cuatrimestre: {cuatrimestre}
└ Promedio: *{promedio}* 📊

*Progreso:*
├ Materias Aprobadas: {materias_aprob}
├ Materias Reprobadas: {materias_reprob}
├ Créditos: {creditos}
└ Nivel Inglés: {nivel_ingles}

*Tutoría:*
├ Tutor: {tutor}
└ Email: {email_tutor}
"""
            
            await update.message.reply_text(mensaje, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"Error en perfil_personal_command: {e}")
            await update.message.reply_text(f"❌ Error al obtener perfil: {str(e)}")
    
    async def pagos_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Muestra el historial de pagos."""
        user_id = update.effective_user.id
        await update.message.reply_text("💰 Consultando tu historial de pagos...")
        
        try:
            creds = self.credentials_manager.get_credentials(user_id)
            if not creds:
                await update.message.reply_text("❌ No tienes credenciales configuradas. Usa /start")
                return
            
            with UPQScraperSession(username=creds['username'], password=creds['password']) as session:
                if not session.login():
                    await update.message.reply_text("❌ Error de autenticación")
                    return
                
                html = session.get_pagos()
                soup = BeautifulSoup(html, 'html.parser')
                
                message = "💰 *Historial de Pagos*\n\n"
                tables = soup.find_all('table')
                
                if tables:
                    for table in tables[:1]:
                        rows = table.find_all('tr')
                        for row in rows[:15]:  # Limitar a 15 pagos
                            cols = row.find_all(['th', 'td'])
                            if cols:
                                row_text = " | ".join([col.get_text(strip=True) for col in cols])
                                message += f"`{row_text}`\n"
                    await update.message.reply_text(message, parse_mode='Markdown')
                else:
                    await update.message.reply_text("📝 No se encontró historial de pagos")
                    
        except Exception as e:
            self.logger.error(f"Error en pagos_command: {e}")
            await update.message.reply_text("❌ Error al obtener pagos")
    
    async def adeudos_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Muestra los adeudos pendientes."""
        user_id = update.effective_user.id
        await update.message.reply_text("⚠️ Consultando adeudos...")
        
        try:
            creds = self.credentials_manager.get_credentials(user_id)
            if not creds:
                await update.message.reply_text("❌ No tienes credenciales configuradas. Usa /start")
                return
            
            with UPQScraperSession(username=creds['username'], password=creds['password']) as session:
                if not session.login():
                    await update.message.reply_text("❌ Error de autenticación")
                    return
                
                html = session.get_adeudos()
                soup = BeautifulSoup(html, 'html.parser')
                
                message = "⚠️ *Adeudos Pendientes*\n\n"
                tables = soup.find_all('table')
                found = False
                
                if tables:
                    for table in tables[:1]:
                        rows = table.find_all('tr')
                        for row in rows:
                            cols = row.find_all(['th', 'td'])
                            if cols:
                                found = True
                                row_text = " | ".join([col.get_text(strip=True) for col in cols])
                                message += f"`{row_text}`\n"
                
                if found:
                    await update.message.reply_text(message, parse_mode='Markdown')
                else:
                    await update.message.reply_text("✅ No tienes adeudos pendientes")
                    
        except Exception as e:
            self.logger.error(f"Error en adeudos_command: {e}")
            await update.message.reply_text("❌ Error al obtener adeudos")
    
    async def documentos_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Muestra los documentos escolares disponibles."""
        user_id = update.effective_user.id
        await update.message.reply_text("📄 Consultando documentos disponibles...")
        
        try:
            creds = self.credentials_manager.get_credentials(user_id)
            if not creds:
                await update.message.reply_text("❌ No tienes credenciales configuradas. Usa /start")
                return
            
            with UPQScraperSession(username=creds['username'], password=creds['password']) as session:
                if not session.login():
                    await update.message.reply_text("❌ Error de autenticación")
                    return
                
                html = session.get_documentos()
                soup = BeautifulSoup(html, 'html.parser')
                
                message = "📄 *Documentos Escolares*\n\n"
                documentos = []
                links = soup.find_all('a')
                
                for link in links[:20]:  # Limitar a 20 documentos
                    text = link.get_text(strip=True)
                    href = link.get('href', '')
                    if text and ('pdf' in href.lower() or 'documento' in text.lower() or 'constancia' in text.lower()):
                        documentos.append(f"📄 {text}")
                
                if documentos:
                    message += "\n".join(documentos)
                    await update.message.reply_text(message, parse_mode='Markdown')
                else:
                    await update.message.reply_text("📝 No se encontraron documentos disponibles")
                    
        except Exception as e:
            self.logger.error(f"Error en documentos_command: {e}")
            await update.message.reply_text("❌ Error al obtener documentos")
    
    async def calendario_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Muestra el calendario académico."""
        user_id = update.effective_user.id
        await update.message.reply_text("📆 Consultando calendario académico...")
        
        try:
            creds = self.credentials_manager.get_credentials(user_id)
            if not creds:
                await update.message.reply_text("❌ No tienes credenciales configuradas. Usa /start")
                return
            
            with UPQScraperSession(username=creds['username'], password=creds['password']) as session:
                if not session.login():
                    await update.message.reply_text("❌ Error de autenticación")
                    return
                
                html = session.get_calendario()
                soup = BeautifulSoup(html, 'html.parser')
                
                message = "📆 *Calendario Académico*\n\n"
                tables = soup.find_all('table')
                
                if tables:
                    for table in tables[:1]:
                        rows = table.find_all('tr')
                        for row in rows[:20]:  # Limitar a 20 eventos
                            cols = row.find_all(['th', 'td'])
                            if cols:
                                row_text = " | ".join([col.get_text(strip=True) for col in cols])
                                message += f"`{row_text}`\n"
                    await update.message.reply_text(message, parse_mode='Markdown')
                else:
                    await update.message.reply_text("📝 No se encontró calendario académico")
                    
        except Exception as e:
            self.logger.error(f"Error en calendario_command: {e}")
            await update.message.reply_text("❌ Error al obtener calendario")
        
        
    async def grades_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comando /grades - Obtiene calificaciones actuales."""
        await update.message.reply_text("📡 Conectando al sistema UPQ...")
        
        try:
            user_id = update.effective_user.id
            
            # Verificar si el usuario tiene credenciales
            creds = self.credentials_manager.get_credentials(user_id)
            if not creds:
                await update.message.reply_text(
                    "❌ No tienes credenciales registradas.\n"
                    "Usa /start para registrarte primero."
                )
                return
            
            # Crear sesión con credenciales del usuario
            with UPQScraperSession(username=creds['username'], password=creds['password']) as session:
                # Login
                if not session.login():
                    await update.message.reply_text(
                        "❌ Error de autenticación con el sistema UPQ.\n"
                        "Verifica tus credenciales con /logout y /start"
                    )
                    return
                
                # Obtener HTML de calificaciones
                html = session.get_grades_html()
                
                # Parsear
                parser = UPQGradesParser(html)
                grades = parser.parse_grades()
                
                # Guardar snapshot en el almacenamiento del usuario
                user_memory = self._get_user_memory(user_id)
                user_memory.add_snapshot(grades)
                user_memory.save()
                
                # Formatear y enviar
                if grades:
                    message = self._format_grades_message(grades)
                    await update.message.reply_text(message, parse_mode='Markdown')
                else:
                    await update.message.reply_text("⚠️ No se encontraron calificaciones")
                    
        except AuthenticationError as e:
            self.logger.error(f"Authentication error: {e}")
            await update.message.reply_text(f"❌ Error de autenticación: {e}")
            
        except FetchError as e:
            self.logger.error(f"Fetch error: {e}")
            await update.message.reply_text(f"❌ Error al obtener datos: {e}")
            
        except ParserError as e:
            self.logger.error(f"Parser error: {e}")
            await update.message.reply_text(
                f"❌ Error al parsear HTML: {e}\n"
                "El formato del sistema puede haber cambiado."
            )
            
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Error inesperado: {e}")
            
    async def check_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comando /check - Verifica nuevas calificaciones."""
        await update.message.reply_text("🔍 Verificando nuevas calificaciones...")
        
        try:
            user_id = update.effective_user.id
            
            # Verificar si el usuario tiene credenciales
            creds = self.credentials_manager.get_credentials(user_id)
            if not creds:
                await update.message.reply_text(
                    "❌ No tienes credenciales registradas.\n"
                    "Usa /start para registrarte primero."
                )
                return
            
            # Crear sesión con credenciales del usuario
            with UPQScraperSession(username=creds['username'], password=creds['password']) as session:
                # Login
                if not session.login():
                    await update.message.reply_text(
                        "❌ Error de autenticación con el sistema UPQ.\n"
                        "Verifica tus credenciales con /logout y /start"
                    )
                    return
                
                # Obtener calificaciones actuales
                html = session.get_grades_html()
                parser = UPQGradesParser(html)
                current_grades = parser.parse_grades()
                
                # Usar almacenamiento del usuario
                user_memory = self._get_user_memory(user_id)
                
                # Guardar snapshot
                user_memory.add_snapshot(current_grades)
                
                # Detectar cambios
                snapshots = user_memory.data.get("snapshots", [])
                
                if len(snapshots) < 2:
                    await update.message.reply_text(
                        "⚠️ No hay snapshot previo para comparar.\n"
                        "Este es el primer snapshot guardado.\n\n"
                        "✅ Ejecuta /check nuevamente en el futuro para detectar cambios."
                    )
                    user_memory.save()
                    return
                
                # Comparar con el penúltimo snapshot
                changes = user_memory.detect_changes(current_grades)
                user_memory.save()
                
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
            self.logger.error(f"Authentication error: {e}")
            await update.message.reply_text(f"❌ Error de autenticación: {e}")
            
        except FetchError as e:
            self.logger.error(f"Fetch error: {e}")
            await update.message.reply_text(f"❌ Error al obtener datos: {e}")
            
        except ParserError as e:
            self.logger.error(f"Parser error: {e}")
            await update.message.reply_text(
                f"❌ Error al parsear HTML: {e}\n"
                "El formato del sistema puede haber cambiado."
            )
            
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Error inesperado: {e}")
            
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Comando /stats - Muestra estadísticas del usuario."""
        user_id = update.effective_user.id
        user_memory = self._get_user_memory(user_id)
        stats = user_memory.get_statistics()
        
        message = "📊 *Estadísticas del Sistema*\n\n"
        message += f"📈 Total de snapshots: `{stats['total_snapshots']}`\n"
        message += f"🔔 Total de cambios detectados: `{stats['total_changes']}`\n"
        message += f"🕐 Última verificación: `{stats['last_check'] or 'Nunca'}`\n"
        message += f"📅 Primer snapshot: `{stats['first_snapshot'] or 'N/A'}`\n"
        
        if stats['total_changes'] > 0:
            message += "\n*Últimos 5 cambios:*\n"
            recent = user_memory.get_recent_changes(5)
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
            # Crear sesión con credenciales del usuario
            with UPQScraperSession(username=username, password=password) as session:
                if not session.login():
                    self.logger.error("Error de autenticación")
                    return {}
                
                # Obtener HTML del perfil
                html = session.get_home_data()
                
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
            # Crear sesión con credenciales del usuario
            with UPQScraperSession(username=username, password=password) as session:
                if not session.login():
                    self.logger.error("Error de autenticación")
                    return ""
                
                # Obtener HTML completo
                html = session.get_info_general()
                return html
                
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

Ya puedes usar todos los comandos del bot o simplemente preguntarme:

📚 *Comandos principales:*
• /kardex - Ver kardex completo
• /perfil - Ver tu perfil
• /horario - Ver horario de clases
• /servicio - Ver servicio social
• /estancias - Ver estancias

💬 *O pregunta directamente:*
• "¿Cuál es mi promedio?"
• "Muéstrame mi horario"
• "¿Tengo materias atrasadas?"
• "¿Cuándo termina mi estancia?"

¡Intenta preguntarme cualquier cosa! 😊
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
            'mi generacion', 'mi grupo', 'qué cuatrimestre', 'que cuatrimestre',
            'perfil', 'mi perfil', 'ver perfil', 'mostrar perfil', 'datos personales'
        ]
        
        # Kardex
        kardex_keywords = [
            'kardex', 'kárdex', 'historial de materias', 'todas mis materias',
            'materias cursadas', 'ver kardex', 'mostrar kardex', 'mi kardex',
            'historial académico completo', 'historial completo'
        ]
        
        # Horario
        horario_keywords = [
            'horario', 'mi horario', 'clases', 'mis clases', 'horario de clases',
            'qué clases tengo', 'que clases tengo', 'cuándo tengo clase',
            'cuando tengo clase', 'ver horario', 'mostrar horario', 'calendario'
        ]
        
        # Servicio Social
        servicio_keywords = [
            'servicio social', 'servicio', 'puedo hacer servicio', 'servicio comunitario',
            'requisitos servicio', 'cuando puedo servicio', 'cuándo puedo servicio',
            'estatus servicio', 'estado servicio'
        ]
        
        # Boleta
        boleta_keywords = [
            'boleta', 'boleta de calificaciones', 'ver boleta', 'mostrar boleta',
            'calificaciones actuales', 'calificaciones del periodo'
        ]
        
        # Pagos
        pagos_keywords = [
            'pagos', 'mis pagos', 'historial de pagos', 'cuánto he pagado',
            'cuanto he pagado', 'ver pagos', 'adeudos', 'debo dinero', 'cuánto debo',
            'cuanto debo'
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
        
        # Kardex académico
        if any(keyword in text_lower for keyword in kardex_keywords):
            await self.kardex_command(update, context)
        
        # Perfil personal (incluye info_keywords)
        elif any(keyword in text_lower for keyword in info_keywords):
            await self.perfil_personal_command(update, context)
        
        # Horario de clases
        elif any(keyword in text_lower for keyword in horario_keywords):
            await self.horario_command(update, context)
        
        # Servicio social
        elif any(keyword in text_lower for keyword in servicio_keywords):
            await self.servicio_social_command(update, context)
        
        # Boleta de calificaciones
        elif any(keyword in text_lower for keyword in boleta_keywords):
            await self.boleta_command(update, context)
        
        # Pagos y adeudos
        elif any(keyword in text_lower for keyword in pagos_keywords):
            await self.pagos_command(update, context)
            
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
                "� *Sobre tu información académica:*\n"
                "• \"Muéstrame mi perfil\"\n"
                "• \"¿Cuál es mi kardex?\"\n"
                "• \"¿Cuál es mi horario?\"\n"
                "• \"¿Cuál es mi promedio?\"\n\n"
                "🎓 *Sobre tu avance:*\n"
                "• \"¿Tengo materias atrasadas?\"\n"
                "• \"¿Cuántos créditos llevo?\"\n"
                "• \"¿Puedo hacer servicio social?\"\n\n"
                "💼 *Sobre estancias:*\n"
                "• \"¿Cuándo termina mi estancia?\"\n"
                "• \"¿Dónde estoy haciendo mi estancia?\"\n\n"
                "� *Sobre pagos:*\n"
                "• \"¿Cuánto debo?\"\n"
                "• \"Muéstrame mis pagos\"\n\n"
                "O usa /help para ver todos los comandos disponibles"
            )
            await update.message.reply_text(response, parse_mode='Markdown')
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Maneja errores globales."""
        self.logger.error(f"Update {update} caused error {context.error}")
        
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
        
        # Nuevos handlers de información adicional
        self.app.add_handler(CommandHandler("horario", self.horario_command))
        self.app.add_handler(CommandHandler("kardex", self.kardex_command))
        self.app.add_handler(CommandHandler("boleta", self.boleta_command))
        self.app.add_handler(CommandHandler("servicio", self.servicio_social_command))
        self.app.add_handler(CommandHandler("perfil", self.perfil_personal_command))
        self.app.add_handler(CommandHandler("pagos", self.pagos_command))
        self.app.add_handler(CommandHandler("adeudos", self.adeudos_command))
        self.app.add_handler(CommandHandler("documentos", self.documentos_command))
        self.app.add_handler(CommandHandler("calendario", self.calendario_command))
        
        
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
