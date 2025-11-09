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


class UPQScraperSession:
    """
    Clase de alto nivel que combina autenticación y fetching.
    Facilita el uso del sistema completo.
    """

    def __init__(self):
        """Inicializa una nueva sesión de scraping."""
        self.authenticator = UPQAuthenticator()
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
