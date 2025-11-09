"""
Configuración centralizada del sistema de scraping UPQ.
Carga variables de entorno desde .env y proporciona configuración global.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
BASE_DIR = Path(__file__).parent.parent
ENV_FILE = BASE_DIR / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    print(f"⚠️  Advertencia: No se encontró el archivo .env en {BASE_DIR}")
    print("   Crea un archivo .env basado en .env.example")


class Settings:
    """Configuración global del sistema."""

    # Credenciales UPQ
    UPQ_USERNAME: str = os.getenv("UPQ_USERNAME", "")
    UPQ_PASSWORD: str = os.getenv("UPQ_PASSWORD", "")

    # URLs del Sistema
    UPQ_BASE_URL: str = os.getenv(
        "UPQ_BASE_URL",
        "https://sistemaintegral.upq.edu.mx"
    )
    UPQ_LOGIN_URL: str = os.getenv(
        "UPQ_LOGIN_URL",
        "https://sistemaintegral.upq.edu.mx/alumnos.php/signin"
    )
    UPQ_GRADES_URL: str = os.getenv(
        "UPQ_GRADES_URL",
        "https://sistemaintegral.upq.edu.mx/alumnos.php/carga-academica"
    )

    # ID de Inscripción (puede ser None para detección automática)
    UPQ_INSCRIPTION_ID: Optional[str] = os.getenv("UPQ_INSCRIPTION_ID")

    # Configuración de Requests
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    USER_AGENT: str = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    VERIFY_SSL: bool = os.getenv("VERIFY_SSL", "true").lower() == "true"

    # Configuración de Storage
    STORAGE_PATH: Path = BASE_DIR / os.getenv(
        "STORAGE_PATH",
        "storage/grades_history.json"
    )

    # Headers HTTP comunes
    HEADERS = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }

    @classmethod
    def validate(cls) -> bool:
        """
        Valida que las credenciales estén configuradas.

        Returns:
            bool: True si las credenciales están configuradas, False en caso contrario.
        """
        if not cls.UPQ_USERNAME or not cls.UPQ_PASSWORD:
            print("❌ Error: Credenciales no configuradas")
            print("   Configura UPQ_USERNAME y UPQ_PASSWORD en el archivo .env")
            return False
        return True

    @classmethod
    def get_login_payload(cls) -> dict:
        """
        Genera el payload para el login.

        Returns:
            dict: Diccionario con las credenciales para POST.
        """
        return {
            "signin[username]": cls.UPQ_USERNAME,
            "signin[password]": cls.UPQ_PASSWORD,
            "signin[_csrf_token]": "",
            "signin[tipo_usuario]": "1",  # Tipo de usuario: 1=Alumno
        }


# Instancia global de configuración
settings = Settings()
