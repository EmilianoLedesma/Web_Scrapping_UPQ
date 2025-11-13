"""
Módulo de autenticación para el sistema UPQ.
Maneja el login y mantiene la sesión activa mediante cookies.
"""

import requests
from pathlib import Path
from typing import Optional, Tuple
from config.settings import settings
import urllib3

# Deshabilitar warning de SSL si está deshabilitada la verificación
if isinstance(settings.VERIFY_SSL, bool) and not settings.VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
elif isinstance(settings.VERIFY_SSL, str):
    bundle_path = settings.VERIFY_SSL
    if not Path(bundle_path).exists():
        print(f"[WARN] Advertencia: El bundle SSL personalizado no existe: {bundle_path}")


class AuthenticationError(Exception):
    """Error de autenticación personalizado."""
    pass


class UPQAuthenticator:
    """
    Clase para manejar la autenticación con el sistema UPQ.
    Usa requests.Session() para mantener cookies entre peticiones.
    """

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        """
        Inicializa el autenticador con una nueva sesión.
        
        Args:
            username: Usuario UPQ (matrícula). Si es None, usa el del .env
            password: Contraseña UPQ. Si es None, usa la del .env
        """
        self.session: requests.Session = requests.Session()
        self.session.headers.update(settings.HEADERS)
        self.is_authenticated: bool = False
        self.inscription_id: Optional[str] = None
        # Credenciales personalizadas o usar las del settings
        self.username = username or settings.UPQ_USERNAME
        self.password = password or settings.UPQ_PASSWORD

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
            if not self.username or not self.password:
                raise AuthenticationError("Credenciales no configuradas")

            print(f"[INFO] Intentando login como: {self.username}")

            # Primero, obtener el formulario de login para extraer el token CSRF
            print("[INFO] Obteniendo formulario de login...")
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
                print(f"[INFO] Token CSRF obtenido: {csrf_token[:20]}...")

            # Preparar payload de login con el token CSRF real
            payload = {
                "signin[username]": self.username,
                "signin[password]": self.password,
                "signin[_csrf_token]": csrf_token,
                "signin[tipo_usuario]": "1"  # 1 = alumno (campo requerido)
            }

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
            print("[INFO] HTML de login guardado en: debug_login_response.html")
            print(f"[INFO] Status code: {response.status_code}, URL final: {response.url}")

            # Verificar si el login fue exitoso
            # El sistema devuelve 200 OK incluso con credenciales incorrectas,
            # por lo que debemos verificar el contenido de la respuesta
            if self._verify_login_success(response):
                self.is_authenticated = True
                print("[OK] Login exitoso")

                # Mostrar cookies para debug
                cookies = list(self.session.cookies)
                if cookies:
                    print(f"[INFO] Cookies de sesión: {len(cookies)} cookie(s)")
                    for cookie in cookies:
                        print(f"   - {cookie.name}")
                else:
                    print("[WARN] No se recibieron cookies de sesión")

                # Intentar extraer el ID de inscripción
                self._extract_inscription_id(response)

                # Si no se detectó y NO estamos usando credenciales del .env,
                # SIEMPRE intentar desde endpoints adicionales
                if not self.inscription_id or self.username != settings.UPQ_USERNAME:
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
        # CRÍTICO: Si la URL final contiene 'signin', significa que el login falló
        # y el sistema nos devolvió al formulario de login
        if 'signin' in response.url:
            print("[ERROR] Login falló - Aún en página de signin")
            return False

        # Verificar si hay redirección a página de alumno (sin signin)
        if 'alumnos.php' in response.url:
            print(f"[OK] Redirigido a: {response.url}")
            return True

        # Verificar en el contenido HTML
        content = response.text.lower()

        # Indicadores de login fallido - verificar PRIMERO
        fail_indicators = [
            'usuario o contraseña incorrectos',
            'credenciales inválidas',
            'login failed',
            'error de autenticación',
            'name="signin[username]"',  # Formulario de login presente
            'action="/alumnos.php/signin"'  # Formulario de login
        ]
        
        if any(indicator in content for indicator in fail_indicators):
            print("[ERROR] Login falló - Detectado indicador de fallo en HTML")
            return False

        # Indicadores de login exitoso
        success_indicators = [
            'carga académica',
            'calificaciones',
            'bienvenido',
            'cerrar sesión',
            'horario'
        ]
        
        if any(indicator in content for indicator in success_indicators):
            print("[OK] Login exitoso - Detectado indicador de éxito en HTML")
            return True

        # Si llegamos aquí, el login probablemente falló
        print("[WARN] No se pudo determinar el estado del login")
        return False

    def _extract_inscription_id(self, response: requests.Response) -> None:
        """
        Intenta extraer el ID de inscripción del HTML de respuesta.

        Args:
            response: Respuesta HTTP del login.
        """
        content = response.text

        # Buscar patrón común: iid=XXXXXX en el HTML
        import re
        match = re.search(r'iid=(\d+)', content)
        if match:
            self.inscription_id = match.group(1)
            print(f"[INFO] ID de inscripción detectado automáticamente: {self.inscription_id}")
            return
        
        # Si no se encontró en el HTML y estamos usando credenciales del .env,
        # usar el valor configurado como fallback
        if self.username == settings.UPQ_USERNAME and settings.UPQ_INSCRIPTION_ID:
            self.inscription_id = settings.UPQ_INSCRIPTION_ID
            print(f"[INFO] ID de inscripción desde configuración (.env): {self.inscription_id}")
            return
            
        print("[WARN] No se pudo detectar automáticamente el ID de inscripción")
        print("       Se intentará obtener desde otros endpoints...")

    def _try_get_inscription_id(self) -> None:
        """
        Intenta obtener el ID de inscripción desde diferentes endpoints.
        """
        try:
            print("[INFO] Buscando ID de inscripción en la página principal...")

            # Primero intentar desde la página principal de alumnos
            url = f"{settings.UPQ_BASE_URL}/alumnos.php"
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
                    print(f"[OK] ID de inscripción encontrado en página principal: {self.inscription_id}")
                    return

            # Si no se encontró, probar endpoint de inscripciones
            print("[INFO] Intentando obtener ID de inscripción desde endpoint de inscripciones...")
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
                    print(f"[OK] ID de inscripción detectado desde inscripciones: {self.inscription_id}")
                    return

                # Buscar patrones alternativos
                match = re.search(r'inscripcion[_-]?id["\']?\s*[:=]\s*["\']?(\d+)', response.text, re.IGNORECASE)
                if match:
                    self.inscription_id = match.group(1)
                    print(f"[OK] ID de inscripción detectado (patrón alternativo): {self.inscription_id}")
                    return
            
            # Si tampoco funcionó, intentar con carga académica
            print("[INFO] Intentando desde carga académica...")
            url = f"{settings.UPQ_BASE_URL}/alumnos.php/carga-academica"
            response = self.session.get(
                url,
                timeout=settings.REQUEST_TIMEOUT,
                verify=settings.VERIFY_SSL
            )
            
            if response.status_code == 200:
                import re
                match = re.search(r'iid=(\d+)', response.text)
                if match:
                    self.inscription_id = match.group(1)
                    print(f"[OK] ID de inscripción encontrado en carga académica: {self.inscription_id}")
                    return

        except Exception as e:
            print(f"[WARN] Error al intentar obtener ID de inscripción: {str(e)}")

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
        print("[INFO] Sesión cerrada")

    def get_inscription_id(self) -> Optional[str]:
        """
        Retorna el ID de inscripción actual.

        Returns:
            Optional[str]: ID de inscripción o None si no está disponible.
        """
        return self.inscription_id or settings.UPQ_INSCRIPTION_ID
