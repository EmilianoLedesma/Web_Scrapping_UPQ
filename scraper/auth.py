"""
Módulo de autenticación para el sistema UPQ.
Maneja el login y mantiene la sesión activa mediante cookies.
"""

import requests
from typing import Optional, Tuple
from config.settings import settings
import urllib3

# Deshabilitar warning de SSL si está deshabilitada la verificación
if not settings.VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class AuthenticationError(Exception):
    """Error de autenticación personalizado."""
    pass


class UPQAuthenticator:
    """
    Clase para manejar la autenticación con el sistema UPQ.
    Usa requests.Session() para mantener cookies entre peticiones.
    """

    def __init__(self):
        """Inicializa el autenticador con una nueva sesión."""
        self.session: requests.Session = requests.Session()
        self.session.headers.update(settings.HEADERS)
        self.is_authenticated: bool = False
        self.inscription_id: Optional[str] = None

    def login(self) -> bool:
        """
        Realiza el login al sistema UPQ.

        Returns:
            bool: True si el login fue exitoso, False en caso contrario.

        Raises:
            AuthenticationError: Si hay un error en el proceso de autenticación.
        """
        try:
            # Validar credenciales antes de intentar login
            if not settings.validate():
                raise AuthenticationError("Credenciales no configuradas")

            print(f"🔐 Intentando login como: {settings.UPQ_USERNAME}")

            # Primero, obtener el formulario de login para extraer el token CSRF
            print("📋 Obteniendo formulario de login...")
            form_response = self.session.get(
                settings.UPQ_LOGIN_URL,
                timeout=settings.REQUEST_TIMEOUT,
                verify=settings.VERIFY_SSL
            )

            # Extraer token CSRF del HTML
            import re
            csrf_match = re.search(r'name="signin\[_csrf_token\]"[^>]*value="([^"]*)"', form_response.text)
            csrf_token = csrf_match.group(1) if csrf_match else ""
            if csrf_token:
                print(f"🔑 Token CSRF obtenido: {csrf_token[:20]}...")

            # Preparar payload de login con el token CSRF real
            payload = settings.get_login_payload()
            if csrf_token:
                payload["signin[_csrf_token]"] = csrf_token

            # Realizar petición POST de login
            response = self.session.post(
                settings.UPQ_LOGIN_URL,
                data=payload,
                timeout=settings.REQUEST_TIMEOUT,
                allow_redirects=True,
                verify=settings.VERIFY_SSL
            )

            # Verificar código de respuesta
            response.raise_for_status()

            # Guardar HTML de login para debug
            with open("debug_login_response.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"💾 HTML de login guardado en: debug_login_response.html")
            print(f"📊 Status code: {response.status_code}, URL final: {response.url}")

            # Verificar si el login fue exitoso
            # El sistema devuelve 200 OK incluso con credenciales incorrectas,
            # por lo que debemos verificar el contenido de la respuesta
            if self._verify_login_success(response):
                self.is_authenticated = True
                print("✅ Login exitoso")

                # Mostrar cookies para debug
                cookies = list(self.session.cookies)
                if cookies:
                    print(f"🍪 Cookies de sesión: {len(cookies)} cookie(s)")
                    for cookie in cookies:
                        print(f"   - {cookie.name}")
                else:
                    print("⚠️  No se recibieron cookies de sesión")

                # Intentar extraer el ID de inscripción
                self._extract_inscription_id(response)

                # Si no se detectó, intentar desde el endpoint de inscripciones
                if not self.inscription_id:
                    self._try_get_inscription_id()

                return True
            else:
                raise AuthenticationError(
                    "Login fallido - Credenciales incorrectas o sistema no disponible"
                )

        except requests.exceptions.Timeout:
            raise AuthenticationError(
                f"Timeout al conectar con {settings.UPQ_LOGIN_URL} - "
                "El servidor tardó demasiado en responder"
            )
        except requests.exceptions.ConnectionError as e:
            raise AuthenticationError(
                f"Error de conexión - Verifica tu conexión a internet o "
                f"si el sistema UPQ está disponible. Detalles: {str(e)}"
            )
        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"Error en la petición HTTP: {str(e)}")

    def _verify_login_success(self, response: requests.Response) -> bool:
        """
        Verifica si el login fue exitoso analizando la respuesta.

        Args:
            response: Respuesta HTTP del login.

        Returns:
            bool: True si el login fue exitoso.
        """
        # Verificar cookies de sesión
        if 'PHPSESSID' in self.session.cookies:
            # El sistema PHP mantiene sesión con esta cookie
            return True

        # Verificar si hay redirección a página de alumno
        if 'alumnos.php' in response.url and 'signin' not in response.url:
            return True

        # Verificar en el contenido HTML
        content = response.text.lower()

        # Indicadores de login fallido
        if any(indicator in content for indicator in [
            'usuario o contraseña incorrectos',
            'credenciales inválidas',
            'login failed',
            'error de autenticación'
        ]):
            return False

        # Indicadores de login exitoso
        if any(indicator in content for indicator in [
            'carga académica',
            'calificaciones',
            'bienvenido',
            'alumno'
        ]):
            return True

        # Si llegamos aquí y tenemos cookies, asumimos éxito
        return len(self.session.cookies) > 0

    def _extract_inscription_id(self, response: requests.Response) -> None:
        """
        Intenta extraer el ID de inscripción del HTML de respuesta.

        Args:
            response: Respuesta HTTP del login.
        """
        # Si ya está configurado en settings, usarlo
        if settings.UPQ_INSCRIPTION_ID:
            self.inscription_id = settings.UPQ_INSCRIPTION_ID
            print(f"📋 ID de inscripción configurado: {self.inscription_id}")
            return

        # Intentar extraer del HTML (puede variar según el sistema)
        # Esto es un placeholder - se puede mejorar con parseo específico
        content = response.text

        # Buscar patrón común: iid=XXXXXX
        import re
        match = re.search(r'iid=(\d+)', content)
        if match:
            self.inscription_id = match.group(1)
            print(f"📋 ID de inscripción detectado: {self.inscription_id}")
        else:
            print("⚠️  No se pudo detectar automáticamente el ID de inscripción")
            print("   Configura UPQ_INSCRIPTION_ID en .env si es necesario")

    def _try_get_inscription_id(self) -> None:
        """
        Intenta obtener el ID de inscripción desde el endpoint de inscripciones.
        """
        try:
            print("🔍 Intentando obtener ID de inscripción desde endpoint...")

            # Probar endpoint de inscripciones
            url = f"{settings.UPQ_BASE_URL}/alumnos.php/inscripcion"
            response = self.session.get(
                url,
                timeout=settings.REQUEST_TIMEOUT,
                verify=settings.VERIFY_SSL
            )

            if response.status_code == 200:
                import re
                # Buscar iid= en el HTML
                match = re.search(r'iid=(\d+)', response.text)
                if match:
                    self.inscription_id = match.group(1)
                    print(f"✅ ID de inscripción detectado: {self.inscription_id}")
                    return

                # Buscar patrones alternativos
                match = re.search(r'inscripcion[_-]?id["\']?\s*[:=]\s*["\']?(\d+)', response.text, re.IGNORECASE)
                if match:
                    self.inscription_id = match.group(1)
                    print(f"✅ ID de inscripción detectado: {self.inscription_id}")
                    return

        except Exception as e:
            print(f"⚠️  Error al intentar obtener ID de inscripción: {str(e)}")

    def get_session(self) -> requests.Session:
        """
        Retorna la sesión autenticada.

        Returns:
            requests.Session: Sesión con cookies activas.

        Raises:
            AuthenticationError: Si no se ha autenticado previamente.
        """
        if not self.is_authenticated:
            raise AuthenticationError(
                "No autenticado - Ejecuta login() primero"
            )
        return self.session

    def logout(self) -> None:
        """Cierra la sesión y limpia las cookies."""
        self.session.cookies.clear()
        self.is_authenticated = False
        self.inscription_id = None
        print("👋 Sesión cerrada")

    def get_inscription_id(self) -> Optional[str]:
        """
        Retorna el ID de inscripción actual.

        Returns:
            Optional[str]: ID de inscripción o None si no está disponible.
        """
        return self.inscription_id or settings.UPQ_INSCRIPTION_ID
