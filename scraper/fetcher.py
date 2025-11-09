"""
Módulo para realizar peticiones HTTP al sistema UPQ.
Usa la sesión autenticada para obtener datos del sistema.
"""

import requests
import time
from typing import Optional
from config.settings import settings
from scraper.auth import UPQAuthenticator, AuthenticationError


class FetchError(Exception):
    """Error al obtener datos del sistema."""
    pass


class UPQFetcher:
    """
    Clase para obtener datos del sistema UPQ.
    Requiere una sesión autenticada para funcionar.
    """

    def __init__(self, authenticator: UPQAuthenticator):
        """
        Inicializa el fetcher con un autenticador.

        Args:
            authenticator: Instancia de UPQAuthenticator ya autenticada.
        """
        self.authenticator = authenticator
        self.session = authenticator.get_session()

    def fetch_grades_html(self, inscription_id: Optional[str] = None) -> str:
        """
        Obtiene el HTML de la página de calificaciones.

        Args:
            inscription_id: ID de inscripción. Si es None, usa el del autenticador.

        Returns:
            str: HTML de la página de calificaciones.

        Raises:
            FetchError: Si hay un error al obtener los datos.
        """
        # Determinar el ID de inscripción a usar
        iid = inscription_id or self.authenticator.get_inscription_id()

        if not iid:
            raise FetchError(
                "ID de inscripción no disponible. "
                "Configura UPQ_INSCRIPTION_ID en .env o espera a que se detecte automáticamente"
            )

        # Primero visitar la página principal para inicializar la sesión
        try:
            print("🔄 Inicializando sesión...")
            home_url = f"{settings.UPQ_BASE_URL}/alumnos.php"
            home_response = self.session.get(
                home_url,
                timeout=settings.REQUEST_TIMEOUT,
                verify=settings.VERIFY_SSL
            )
            home_response.raise_for_status()
        except Exception as e:
            print(f"⚠️  Advertencia al acceder a página principal: {str(e)}")

        # Construir URL de calificaciones con timestamp (petición AJAX)
        timestamp = int(time.time() * 1000)  # Timestamp en milisegundos
        url = f"{settings.UPQ_GRADES_URL}?iid={iid}&_={timestamp}"

        print(f"📥 Obteniendo calificaciones desde: {url}")

        # Headers adicionales para petición AJAX
        ajax_headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'text/html, */*; q=0.01',
            'Referer': f'{settings.UPQ_BASE_URL}/alumnos.php',
        }

        try:
            # Realizar petición GET con headers AJAX
            response = self.session.get(
                url,
                headers=ajax_headers,
                timeout=settings.REQUEST_TIMEOUT,
                verify=settings.VERIFY_SSL
            )

            # Verificar código de respuesta
            response.raise_for_status()

            # Verificar que no nos hayan redirigido al login
            if 'signin' in response.url:
                raise FetchError(
                    "Sesión expirada - Se requiere login nuevamente"
                )

            print(f"✅ Datos obtenidos exitosamente ({len(response.text)} bytes)")

            return response.text

        except requests.exceptions.Timeout:
            raise FetchError(
                f"Timeout al obtener calificaciones - "
                f"El servidor tardó más de {settings.REQUEST_TIMEOUT}s en responder"
            )
        except requests.exceptions.ConnectionError:
            raise FetchError(
                "Error de conexión - Verifica tu internet o si el sistema está disponible"
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise FetchError(
                    f"Página no encontrada (404) - Verifica el ID de inscripción: {iid}"
                )
            elif e.response.status_code == 403:
                raise FetchError(
                    "Acceso denegado (403) - Posible sesión expirada o permisos insuficientes"
                )
            else:
                raise FetchError(f"Error HTTP {e.response.status_code}: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise FetchError(f"Error en la petición: {str(e)}")

    def fetch_student_info(self) -> str:
        """
        Obtiene información general del alumno (página principal).

        Returns:
            str: HTML de la página principal del alumno.

        Raises:
            FetchError: Si hay un error al obtener los datos.
        """
        url = f"{settings.UPQ_BASE_URL}/alumnos.php"

        print(f"📥 Obteniendo información del alumno...")

        try:
            response = self.session.get(
                url,
                timeout=settings.REQUEST_TIMEOUT,
                verify=settings.VERIFY_SSL
            )

            response.raise_for_status()

            return response.text

        except requests.exceptions.RequestException as e:
            raise FetchError(f"Error al obtener información del alumno: {str(e)}")

    def fetch_inscriptions(self) -> str:
        """
        Obtiene la lista de inscripciones del alumno.
        Útil para detectar automáticamente el ID de inscripción actual.

        Returns:
            str: HTML con las inscripciones.

        Raises:
            FetchError: Si hay un error al obtener los datos.
        """
        url = f"{settings.UPQ_BASE_URL}/alumnos.php/inscripcion"

        print(f"📥 Obteniendo inscripciones...")

        try:
            response = self.session.get(
                url,
                timeout=settings.REQUEST_TIMEOUT,
                verify=settings.VERIFY_SSL
            )

            response.raise_for_status()

            return response.text

        except requests.exceptions.RequestException as e:
            raise FetchError(f"Error al obtener inscripciones: {str(e)}")
    
    def fetch_home_data(self) -> str:
        """
        Obtiene el HTML de la página home/home con el perfil del estudiante.

        Returns:
            str: HTML de la página home con información del perfil.

        Raises:
            FetchError: Si hay un error al obtener los datos.
        """
        url = f"{settings.UPQ_BASE_URL}/alumnos.php/home/home"

        print(f"📥 Obteniendo datos del perfil...")

        try:
            response = self.session.get(
                url,
                timeout=settings.REQUEST_TIMEOUT,
                verify=settings.VERIFY_SSL
            )

            response.raise_for_status()

            print(f"✅ Perfil obtenido ({len(response.text)} bytes)")
            return response.text

        except requests.exceptions.RequestException as e:
            raise FetchError(f"Error al obtener datos del perfil: {str(e)}")
    
    def fetch_info_general(self) -> str:
        """
        Obtiene el HTML completo de información general del alumno.
        Incluye: historial, estancias, talleres, servicio social, etc.

        Returns:
            str: HTML con toda la información general del alumno.

        Raises:
            FetchError: Si hay un error al obtener los datos.
        """
        # Usar el mid (menu id) conocido para información general
        url = f"{settings.UPQ_BASE_URL}/alumnos.php/alumno_informacion_general?mid=16746"

        print(f"📥 Obteniendo información general completa...")

        try:
            response = self.session.get(
                url,
                timeout=settings.REQUEST_TIMEOUT,
                verify=settings.VERIFY_SSL
            )

            response.raise_for_status()

            print(f"✅ Información general obtenida ({len(response.text)} bytes)")
            return response.text

        except requests.exceptions.RequestException as e:
            raise FetchError(f"Error al obtener información general: {str(e)}")
    
    def fetch_horario(self, inscription_id: Optional[str] = None) -> str:
        """
        Obtiene el horario de clases del estudiante.

        Args:
            inscription_id: ID de inscripción. Si es None, usa el del autenticador.

        Returns:
            str: HTML con el horario de clases.

        Raises:
            FetchError: Si hay un error al obtener los datos.
        """
        # Determinar el ID de inscripción a usar
        iid = inscription_id or self.authenticator.get_inscription_id()

        if not iid:
            raise FetchError(
                "ID de inscripción no disponible. "
                "Configura UPQ_INSCRIPTION_ID en .env o espera a que se detecte automáticamente"
            )

        # Agregar timestamp para evitar cache
        timestamp = int(time.time() * 1000)
        url = f"{settings.UPQ_BASE_URL}/alumnos.php/horario-materias?iid={iid}&_={timestamp}"

        print(f"📅 Obteniendo horario de clases...")

        # Headers AJAX
        ajax_headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': '*/*',
            'Referer': f'{settings.UPQ_BASE_URL}/alumnos.php/home/home',
        }

        try:
            response = self.session.get(
                url,
                headers=ajax_headers,
                timeout=settings.REQUEST_TIMEOUT,
                verify=settings.VERIFY_SSL
            )

            response.raise_for_status()

            print(f"✅ Horario obtenido ({len(response.text)} bytes)")
            return response.text

        except requests.exceptions.RequestException as e:
            raise FetchError(f"Error al obtener horario: {str(e)}")
    
    # NOTA: Estos endpoints NO existen según la exploración del sistema:
    # - /alumnos.php/kardex (404)
    # - /alumnos.php/perfil (404)  
    # - /alumnos.php/servicio-social (no confirmado)
    # Si necesitas esta información, usa fetch_info_general() que contiene todo
    
    def fetch_kardex(self) -> str:
        """
        Obtiene el kardex académico completo del alumno.
        
        El kardex está disponible en /alumnos.php/calificaciones como uno de los tabs.
        Este endpoint contiene: Boleta, Historial Académico, Materias No Acreditadas y Kardex.

        Returns:
            str: HTML de la página de calificaciones que incluye el kardex.

        Raises:
            FetchError: Si hay un error al obtener los datos.
        """
        # Según exploracion_completa_sii.json, el kardex está en /calificaciones
        timestamp = int(time.time() * 1000)
        url = f"{settings.UPQ_BASE_URL}/alumnos.php/calificaciones?_={timestamp}"

        print(f"📚 Obteniendo kardex académico desde /calificaciones...")

        # Headers AJAX como en EndpointsExplorables.md
        ajax_headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': '*/*',
            'Referer': f'{settings.UPQ_BASE_URL}/alumnos.php/home/home',
        }

        try:
            response = self.session.get(
                url,
                headers=ajax_headers,
                timeout=settings.REQUEST_TIMEOUT,
                verify=settings.VERIFY_SSL
            )

            response.raise_for_status()

            print(f"✅ Kardex obtenido ({len(response.text)} bytes)")
            return response.text

        except requests.exceptions.RequestException as e:
            raise FetchError(f"Error al obtener kardex: {str(e)}")
    
    def fetch_boleta(self) -> str:
        """
        Obtiene la boleta de calificaciones completa.

        Returns:
            str: HTML con la boleta de calificaciones.

        Raises:
            FetchError: Si hay un error al obtener los datos.
        """
        url = f"{settings.UPQ_BASE_URL}/alumnos.php/boleta-calificaciones"

        print(f"📋 Obteniendo boleta de calificaciones...")

        try:
            response = self.session.get(
                url,
                timeout=settings.REQUEST_TIMEOUT,
                verify=settings.VERIFY_SSL
            )

            response.raise_for_status()

            print(f"✅ Boleta obtenida ({len(response.text)} bytes)")
            return response.text

        except requests.exceptions.RequestException as e:
            raise FetchError(f"Error al obtener boleta: {str(e)}")
    
    def fetch_servicio_social(self) -> str:
        """
        NOTA: El endpoint /servicio-social no existe como endpoint independiente.
        La información del servicio social está disponible en fetch_info_general().

        Returns:
            str: Mensaje informativo redirigiendo a info_general.

        Raises:
            FetchError: Siempre, ya que este endpoint no existe.
        """
        raise FetchError(
            "El endpoint /servicio-social no existe. "
            "Usa fetch_info_general() o get_info_general() para obtener información del servicio social."
        )
    
    def fetch_perfil(self) -> str:
        """
        Obtiene el perfil personal del alumno desde la página home.
        
        La página home contiene todos los datos del perfil del estudiante:
        nombre completo, matrícula, carrera, generación, grupo, cuatrimestre,
        promedio general, materias aprobadas, créditos, nivel de inglés,
        estatus, NSS, tutor y email del tutor.

        Returns:
            str: HTML de la página home con datos del perfil.

        Raises:
            FetchError: Si hay un error al obtener los datos.
        """
        # El perfil completo está en la página home
        return self.fetch_home_data()
    
    def fetch_pagos(self) -> str:
        """
        Obtiene el historial de pagos y colegiaturas.

        Returns:
            str: HTML con historial de pagos.

        Raises:
            FetchError: Si hay un error al obtener los datos.
        """
        # Agregar timestamp para evitar cache (como en EndpointsExplorables.md)
        timestamp = int(time.time() * 1000)
        url = f"{settings.UPQ_BASE_URL}/alumnos.php/pagos?_={timestamp}"

        print(f"💰 Obteniendo historial de pagos...")

        # Headers AJAX
        ajax_headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': '*/*',
            'Referer': f'{settings.UPQ_BASE_URL}/alumnos.php/home/home',
        }

        try:
            response = self.session.get(
                url,
                headers=ajax_headers,
                timeout=settings.REQUEST_TIMEOUT,
                verify=settings.VERIFY_SSL
            )

            response.raise_for_status()

            print(f"✅ Pagos obtenidos ({len(response.text)} bytes)")
            return response.text

        except requests.exceptions.RequestException as e:
            raise FetchError(f"Error al obtener pagos: {str(e)}")
    
    def fetch_adeudos(self) -> str:
        """
        Obtiene los adeudos pendientes.

        Returns:
            str: HTML con adeudos pendientes.

        Raises:
            FetchError: Si hay un error al obtener los datos.
        """
        # Endpoint correcto según EndpointsExplorables.md
        url = f"{settings.UPQ_BASE_URL}/alumnos.php/controlpagos/pagosEnAdeudos"

        print(f"⚠️ Obteniendo adeudos...")

        # Headers AJAX
        ajax_headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'text/html, */*; q=0.01',
            'Referer': f'{settings.UPQ_BASE_URL}/alumnos.php/home/home',
        }

        try:
            response = self.session.get(
                url,
                headers=ajax_headers,
                timeout=settings.REQUEST_TIMEOUT,
                verify=settings.VERIFY_SSL
            )

            response.raise_for_status()

            print(f"✅ Adeudos obtenidos ({len(response.text)} bytes)")
            return response.text

        except requests.exceptions.RequestException as e:
            raise FetchError(f"Error al obtener adeudos: {str(e)}")
    
    def fetch_documentos(self) -> str:
        """
        Obtiene la lista de documentos escolares disponibles.

        Returns:
            str: HTML con documentos disponibles.

        Raises:
            FetchError: Si hay un error al obtener los datos.
        """
        # Endpoint correcto según EndpointsExplorables.md
        url = f"{settings.UPQ_BASE_URL}/alumnos.php/documentos-en-proceso"

        print(f"📄 Obteniendo documentos escolares...")

        # Headers AJAX
        ajax_headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'text/html, */*; q=0.01',
            'Referer': f'{settings.UPQ_BASE_URL}/alumnos.php/home/home',
        }

        try:
            response = self.session.get(
                url,
                headers=ajax_headers,
                timeout=settings.REQUEST_TIMEOUT,
                verify=settings.VERIFY_SSL
            )

            response.raise_for_status()

            print(f"✅ Documentos obtenidos ({len(response.text)} bytes)")
            return response.text

        except requests.exceptions.RequestException as e:
            raise FetchError(f"Error al obtener documentos: {str(e)}")
    
    def fetch_calendario(self) -> str:
        """
        Obtiene el seguimiento cuatrimestral (calendario académico).

        Returns:
            str: HTML con el calendario académico.

        Raises:
            FetchError: Si hay un error al obtener los datos.
        """
        # Endpoint correcto según EndpointsExplorables.md
        timestamp = int(time.time() * 1000)
        url = f"{settings.UPQ_BASE_URL}/alumnos.php/seguimiento-cuatrimestral?_={timestamp}"

        print(f"📆 Obteniendo calendario académico...")

        # Headers AJAX
        ajax_headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': '*/*',
            'Referer': f'{settings.UPQ_BASE_URL}/alumnos.php/home/home',
        }

        try:
            response = self.session.get(
                url,
                headers=ajax_headers,
                timeout=settings.REQUEST_TIMEOUT,
                verify=settings.VERIFY_SSL
            )

            response.raise_for_status()

            print(f"✅ Calendario obtenido ({len(response.text)} bytes)")
            return response.text

        except requests.exceptions.RequestException as e:
            raise FetchError(f"Error al obtener calendario: {str(e)}")
    
    def fetch_historial_academico(self) -> str:
        """
        Obtiene el historial académico completo del estudiante.
        
        Endpoint: /alumnos.php/historial-academico
        Contiene: Todas las materias cursadas con fecha, ciclo, créditos,
                  calificación, tipo de evaluación y estado.

        Returns:
            str: HTML con el historial académico completo.

        Raises:
            FetchError: Si hay un error al obtener los datos.
        """
        timestamp = int(time.time() * 1000)
        url = f"{settings.UPQ_BASE_URL}/alumnos.php/historial-academico?_={timestamp}"

        print(f"📖 Obteniendo historial académico...")

        ajax_headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': '*/*',
            'Referer': f'{settings.UPQ_BASE_URL}/alumnos.php/home/home',
        }

        try:
            response = self.session.get(
                url,
                headers=ajax_headers,
                timeout=settings.REQUEST_TIMEOUT,
                verify=settings.VERIFY_SSL
            )

            response.raise_for_status()

            print(f"✅ Historial académico obtenido ({len(response.text)} bytes)")
            return response.text

        except requests.exceptions.RequestException as e:
            raise FetchError(f"Error al obtener historial académico: {str(e)}")
    
    def fetch_carga_academica(self, inscription_id: Optional[str] = None) -> str:
        """
        Obtiene la carga académica actual del estudiante.
        
        Endpoint: /alumnos.php/carga-academica?iid={iid}
        Contiene: Materias del cuatrimestre en curso con calificaciones parciales,
                  profesor, aula y grupo.

        Args:
            inscription_id: ID de inscripción. Si es None, usa el del autenticador.

        Returns:
            str: HTML con la carga académica actual.

        Raises:
            FetchError: Si hay un error al obtener los datos.
        """
        # Obtener iid
        iid = inscription_id or self.authenticator.get_inscription_id()
        if not iid:
            raise FetchError("No se pudo obtener el ID de inscripción")

        timestamp = int(time.time() * 1000)
        url = f"{settings.UPQ_BASE_URL}/alumnos.php/carga-academica?iid={iid}&_={timestamp}"

        print(f"📚 Obteniendo carga académica (iid={iid})...")

        ajax_headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': '*/*',
            'Referer': f'{settings.UPQ_BASE_URL}/alumnos.php/home/home',
        }

        try:
            response = self.session.get(
                url,
                headers=ajax_headers,
                timeout=settings.REQUEST_TIMEOUT,
                verify=settings.VERIFY_SSL
            )

            response.raise_for_status()

            print(f"✅ Carga académica obtenida ({len(response.text)} bytes)")
            return response.text

        except requests.exceptions.RequestException as e:
            raise FetchError(f"Error al obtener carga académica: {str(e)}")
    
    def fetch_pagos_proceso(self) -> str:
        """
        Obtiene los pagos en proceso.
        
        Endpoint: /alumnos.php/pagos-en-proceso
        Contiene: Pagos que están siendo procesados.

        Returns:
            str: HTML con pagos en proceso.

        Raises:
            FetchError: Si hay un error al obtener los datos.
        """
        timestamp = int(time.time() * 1000)
        url = f"{settings.UPQ_BASE_URL}/alumnos.php/pagos-en-proceso?_={timestamp}"

        print(f"⏳ Obteniendo pagos en proceso...")

        ajax_headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'text/html, */*; q=0.01',
            'Referer': f'{settings.UPQ_BASE_URL}/alumnos.php/home/home',
        }

        try:
            response = self.session.get(
                url,
                headers=ajax_headers,
                timeout=settings.REQUEST_TIMEOUT,
                verify=settings.VERIFY_SSL
            )

            response.raise_for_status()

            print(f"✅ Pagos en proceso obtenidos ({len(response.text)} bytes)")
            return response.text

        except requests.exceptions.RequestException as e:
            raise FetchError(f"Error al obtener pagos en proceso: {str(e)}")
    
    def fetch_inscripcion(self) -> str:
        """
        Obtiene información de inscripción/seguimiento cuatrimestral.
        
        Endpoint: /alumnos.php/inscripcion
        Contiene: Tabs con carga académica, horario y cuatrimestres.

        Returns:
            str: HTML con información de inscripción.

        Raises:
            FetchError: Si hay un error al obtener los datos.
        """
        timestamp = int(time.time() * 1000)
        url = f"{settings.UPQ_BASE_URL}/alumnos.php/inscripcion?_={timestamp}"

        print(f"📝 Obteniendo información de inscripción...")

        ajax_headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': '*/*',
            'Referer': f'{settings.UPQ_BASE_URL}/alumnos.php/home/home',
        }

        try:
            response = self.session.get(
                url,
                headers=ajax_headers,
                timeout=settings.REQUEST_TIMEOUT,
                verify=settings.VERIFY_SSL
            )

            response.raise_for_status()

            print(f"✅ Inscripción obtenida ({len(response.text)} bytes)")
            return response.text

        except requests.exceptions.RequestException as e:
            raise FetchError(f"Error al obtener inscripción: {str(e)}")

    def fetch_info_general(self) -> str:
        """
        Obtiene información general del alumno (mapa curricular completo).
        
        Endpoint: /alumnos.php/alumno_informacion_general
        Contiene: Mapa curricular de todos los cuatrimestres con calificaciones,
                  tipo de evaluación e intentos por materia.

        Returns:
            str: HTML con información general del alumno.

        Raises:
            FetchError: Si hay un error al obtener los datos.
        """
        timestamp = int(time.time() * 1000)
        # mid=16746 es un parámetro que se detecta automáticamente, pero puede variar
        url = f"{settings.UPQ_BASE_URL}/alumnos.php/alumno_informacion_general?mid=16746&_={timestamp}"

        print(f"🎓 Obteniendo información general del alumno...")

        ajax_headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': '*/*',
            'Referer': f'{settings.UPQ_BASE_URL}/alumnos.php/home/home',
        }

        try:
            response = self.session.get(
                url,
                headers=ajax_headers,
                timeout=settings.REQUEST_TIMEOUT,
                verify=settings.VERIFY_SSL
            )

            response.raise_for_status()

            print(f"✅ Información general obtenida ({len(response.text)} bytes)")
            return response.text

        except requests.exceptions.RequestException as e:
            raise FetchError(f"Error al obtener información general: {str(e)}")

    def fetch_servicios(self) -> str:
        """
        Obtiene información de servicios disponibles.
        
        Endpoint: /alumnos.php/servicios
        Contiene: Servicios disponibles para el alumno.

        Returns:
            str: HTML con servicios disponibles.

        Raises:
            FetchError: Si hay un error al obtener los datos.
        """
        timestamp = int(time.time() * 1000)
        url = f"{settings.UPQ_BASE_URL}/alumnos.php/servicios?_={timestamp}"

        print(f"🛠️ Obteniendo servicios disponibles...")

        ajax_headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': '*/*',
            'Referer': f'{settings.UPQ_BASE_URL}/alumnos.php/home/home',
        }

        try:
            response = self.session.get(
                url,
                headers=ajax_headers,
                timeout=settings.REQUEST_TIMEOUT,
                verify=settings.VERIFY_SSL
            )

            response.raise_for_status()

            print(f"✅ Servicios obtenidos ({len(response.text)} bytes)")
            return response.text

        except requests.exceptions.RequestException as e:
            raise FetchError(f"Error al obtener servicios: {str(e)}")


class UPQScraperSession:
    """
    Wrapper de alto nivel para scraping del sistema UPQ.
    Maneja autenticación y fetching de datos.
    """

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        """
        Inicializa una nueva sesión de scraping.
        
        Args:
            username: Matrícula del usuario (opcional, usa .env si no se proporciona)
            password: Contraseña del usuario (opcional, usa .env si no se proporciona)
        """
        self.authenticator = UPQAuthenticator(username=username, password=password)
        self.fetcher: Optional[UPQFetcher] = None

    def __enter__(self):
        """Context manager para uso con 'with' statement."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cierra la sesión al salir del context manager."""
        if self.authenticator.is_authenticated:
            self.authenticator.logout()

    def login(self) -> bool:
        """
        Realiza el login y prepara el fetcher.

        Returns:
            bool: True si el login fue exitoso.
        """
        success = self.authenticator.login()
        if success:
            self.fetcher = UPQFetcher(self.authenticator)
        return success

    def get_grades_html(self) -> str:
        """
        Obtiene el HTML de calificaciones.

        Returns:
            str: HTML de la página de calificaciones.

        Raises:
            FetchError: Si no se ha autenticado o hay error.
        """
        if not self.fetcher:
            raise FetchError("No autenticado - Ejecuta login() primero")

        return self.fetcher.fetch_grades_html()

    def get_student_info(self) -> str:
        """
        Obtiene información del alumno.

        Returns:
            str: HTML con información del alumno.

        Raises:
            FetchError: Si no se ha autenticado o hay error.
        """
        if not self.fetcher:
            raise FetchError("No autenticado - Ejecuta login() primero")

        return self.fetcher.fetch_student_info()
    
    def get_home_data(self) -> str:
        """
        Obtiene datos del perfil desde /home/home.

        Returns:
            str: HTML con datos del perfil del estudiante.

        Raises:
            FetchError: Si no se ha autenticado o hay error.
        """
        if not self.fetcher:
            raise FetchError("No autenticado - Ejecuta login() primero")

        return self.fetcher.fetch_home_data()
    
    def get_info_general(self) -> str:
        """
        Obtiene información general completa del alumno.

        Returns:
            str: HTML con toda la información general.

        Raises:
            FetchError: Si no se ha autenticado o hay error.
        """
        if not self.fetcher:
            raise FetchError("No autenticado - Ejecuta login() primero")

        return self.fetcher.fetch_info_general()
    
    def get_horario(self) -> str:
        """
        Obtiene el horario de clases.

        Returns:
            str: HTML con el horario.

        Raises:
            FetchError: Si no se ha autenticado o hay error.
        """
        if not self.fetcher:
            raise FetchError("No autenticado - Ejecuta login() primero")

        return self.fetcher.fetch_horario()
    
    def get_kardex(self) -> str:
        """
        Obtiene el kardex académico.

        Returns:
            str: HTML con el kardex.

        Raises:
            FetchError: Si no se ha autenticado o hay error.
        """
        if not self.fetcher:
            raise FetchError("No autenticado - Ejecuta login() primero")

        return self.fetcher.fetch_kardex()
    
    def get_boleta(self) -> str:
        """
        Obtiene la boleta de calificaciones.

        Returns:
            str: HTML con la boleta.

        Raises:
            FetchError: Si no se ha autenticado o hay error.
        """
        if not self.fetcher:
            raise FetchError("No autenticado - Ejecuta login() primero")

        return self.fetcher.fetch_boleta()
    
    def get_servicio_social(self) -> str:
        """
        Obtiene información del servicio social.

        Returns:
            str: HTML con servicio social.

        Raises:
            FetchError: Si no se ha autenticado o hay error.
        """
        if not self.fetcher:
            raise FetchError("No autenticado - Ejecuta login() primero")

        return self.fetcher.fetch_servicio_social()
    
    def get_perfil(self) -> str:
        """
        Obtiene el perfil personal.

        Returns:
            str: HTML con datos personales.

        Raises:
            FetchError: Si no se ha autenticado o hay error.
        """
        if not self.fetcher:
            raise FetchError("No autenticado - Ejecuta login() primero")

        return self.fetcher.fetch_perfil()
    
    def get_pagos(self) -> str:
        """
        Obtiene el historial de pagos.

        Returns:
            str: HTML con pagos.

        Raises:
            FetchError: Si no se ha autenticado o hay error.
        """
        if not self.fetcher:
            raise FetchError("No autenticado - Ejecuta login() primero")

        return self.fetcher.fetch_pagos()
    
    def get_adeudos(self) -> str:
        """
        Obtiene los adeudos pendientes.

        Returns:
            str: HTML con adeudos.

        Raises:
            FetchError: Si no se ha autenticado o hay error.
        """
        if not self.fetcher:
            raise FetchError("No autenticado - Ejecuta login() primero")

        return self.fetcher.fetch_adeudos()
    
    def get_documentos(self) -> str:
        """
        Obtiene documentos escolares.

        Returns:
            str: HTML con documentos.

        Raises:
            FetchError: Si no se ha autenticado o hay error.
        """
        if not self.fetcher:
            raise FetchError("No autenticado - Ejecuta login() primero")

        return self.fetcher.fetch_documentos()
    
    def get_calendario(self) -> str:
        """
        Obtiene el calendario académico.

        Returns:
            str: HTML con el calendario.

        Raises:
            FetchError: Si no se ha autenticado o hay error.
        """
        if not self.fetcher:
            raise FetchError("No autenticado - Ejecuta login() primero")

        return self.fetcher.fetch_calendario()
    
    def get_historial_academico(self) -> str:
        """
        Obtiene el historial académico completo.

        Returns:
            str: HTML con el historial académico.

        Raises:
            FetchError: Si no se ha autenticado o hay error.
        """
        if not self.fetcher:
            raise FetchError("No autenticado - Ejecuta login() primero")

        return self.fetcher.fetch_historial_academico()
    
    def get_carga_academica(self, inscription_id: Optional[str] = None) -> str:
        """
        Obtiene la carga académica actual.

        Args:
            inscription_id: ID de inscripción (opcional).

        Returns:
            str: HTML con la carga académica.

        Raises:
            FetchError: Si no se ha autenticado o hay error.
        """
        if not self.fetcher:
            raise FetchError("No autenticado - Ejecuta login() primero")

        return self.fetcher.fetch_carga_academica(inscription_id)
    
    def get_pagos_proceso(self) -> str:
        """
        Obtiene los pagos en proceso.

        Returns:
            str: HTML con pagos en proceso.

        Raises:
            FetchError: Si no se ha autenticado o hay error.
        """
        if not self.fetcher:
            raise FetchError("No autenticado - Ejecuta login() primero")

        return self.fetcher.fetch_pagos_proceso()
    
    def get_inscripcion(self) -> str:
        """
        Obtiene información de inscripción.

        Returns:
            str: HTML con información de inscripción.

        Raises:
            FetchError: Si no se ha autenticado o hay error.
        """
        if not self.fetcher:
            raise FetchError("No autenticado - Ejecuta login() primero")

        return self.fetcher.fetch_inscripcion()

    def get_info_general(self) -> str:
        """
        Obtiene información general del alumno (mapa curricular).

        Returns:
            str: HTML con información general.

        Raises:
            FetchError: Si no se ha autenticado o hay error.
        """
        if not self.fetcher:
            raise FetchError("No autenticado - Ejecuta login() primero")

        return self.fetcher.fetch_info_general()

    def get_servicios(self) -> str:
        """
        Obtiene servicios disponibles.

        Returns:
            str: HTML con servicios.

        Raises:
            FetchError: Si no se ha autenticado o hay error.
        """
        if not self.fetcher:
            raise FetchError("No autenticado - Ejecuta login() primero")

        return self.fetcher.fetch_servicios()
