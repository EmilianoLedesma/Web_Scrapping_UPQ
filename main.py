#!/usr/bin/env python3
"""
Sistema de Scraping de Calificaciones UPQ - Punto de entrada principal.

Uso:
    python main.py --get-grades      # Obtener calificaciones actuales
    python main.py --check-new       # Detectar nuevas calificaciones
    python main.py --export FILE     # Exportar datos a JSON
    python main.py --stats           # Mostrar estadísticas
"""

import argparse
import sys
import json
import os
from typing import Optional

# Configurar UTF-8 para Windows (soporte de emojis)
if sys.platform == "win32":
    import locale
    # Intentar configurar UTF-8 en la consola de Windows
    try:
        if sys.stdout.encoding != 'utf-8':
            sys.stdout.reconfigure(encoding='utf-8')
        if sys.stderr.encoding != 'utf-8':
            sys.stderr.reconfigure(encoding='utf-8')
    except:
        # Si falla, establecer variable de entorno
        os.environ['PYTHONIOENCODING'] = 'utf-8'

from config.settings import settings
from scraper.fetcher import UPQScraperSession, FetchError
from scraper.parser import UPQGradesParser, ParserError
from scraper.auth import AuthenticationError
from storage.memory import GradesMemory, StorageError


def print_banner():
    """Imprime el banner del sistema."""
    banner = """
╭───────────────────────────────────────────────────────────────╮
│                                                               │
│  🎓  Sistema de Scraping de Calificaciones UPQ           │
│                                                               │
│  🚀  Versión: 1.0.0                                         │
│  💻  Bot de Telegram integrado                             │
│                                                               │
╰───────────────────────────────────────────────────────────────╯
"""
    print(banner)


def get_grades(session: UPQScraperSession, memory: GradesMemory) -> Optional[dict]:
    """
    Obtiene las calificaciones actuales del sistema.

    Args:
        session: Sesión de scraping autenticada.
        memory: Instancia de memoria para almacenamiento.

    Returns:
        Diccionario con las calificaciones o None si hay error.
    """
    try:
        # Obtener HTML de calificaciones y página del alumno (contiene nombre/matrícula)
        print("\n📡 Conectando al sistema UPQ...")
        grades_html = session.get_grades_html()

        # Intentar obtener la página principal del alumno (puede contener nombre y matrícula)
        try:
            student_html = session.get_student_info()
        except Exception:
            student_html = ""

        combined_html = student_html + "\n" + grades_html

        # Guardar HTML para debug
        try:
            with open("debug_grades.html", "w", encoding="utf-8") as f:
                f.write(grades_html)
            if student_html:
                with open("debug_student.html", "w", encoding="utf-8") as f:
                    f.write(student_html)
                print(f"💾 HTML de alumno guardado: debug_student.html")
            print(f"💾 HTML de calificaciones guardado: debug_grades.html")
        except Exception:
            pass

        # Parsear HTML combinado
        print("🔍 Extrayendo calificaciones...")
        parser = UPQGradesParser(combined_html)
        grades_data = parser.parse_grades()

        # Guardar snapshot
        memory.add_snapshot(grades_data)
        memory.save()

        return grades_data

    except FetchError as e:
        print(f"\n❌ Error al obtener datos: {e}")
        return None
    except ParserError as e:
        print(f"\n❌ Error al parsear HTML: {e}")
        print("   El formato del HTML puede haber cambiado")
        return None
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        return None


def check_new_grades(session: UPQScraperSession, memory: GradesMemory) -> None:
    """
    Verifica si hay nuevas calificaciones comparando con el último snapshot.

    Args:
        session: Sesión de scraping autenticada.
        memory: Instancia de memoria para almacenamiento.
    """
    # Obtener calificaciones actuales
    current_grades = get_grades(session, memory)

    if not current_grades:
        print("\n❌ No se pudieron obtener las calificaciones actuales")
        return

    # Detectar cambios (se hace contra el penúltimo snapshot)
    # porque acabamos de agregar uno nuevo
    snapshots = memory.data.get("snapshots", [])

    if len(snapshots) < 2:
        print("\n⚠️  No hay snapshot previo para comparar")
        print("   Este es el primer snapshot guardado")
        print("\n✅ Ejecuta --check-new nuevamente en el futuro para detectar cambios")
        return

    # Comparar con el penúltimo snapshot
    previous_snapshot = snapshots[-2]
    changes = memory.detect_changes(current_grades)

    # Guardar cambios
    memory.save()

    # Mostrar resultados
    print("\n" + "╭" + "─" * 78 + "╮")
    print("│" + " " * 25 + "🔍 RESULTADOS DE COMPARACIÓN" + " " * 24 + "│")
    print("╰" + "─" * 78 + "╯")

    if changes:
        print(f"\n🔔 ¡Se detectaron {len(changes)} cambios!")
        print("\n" + memory.format_changes(changes))
    else:
        print("\n✅ No hay cambios desde la última verificación")
        print(f"   Último check: {previous_snapshot['timestamp']}")


def show_statistics(memory: GradesMemory) -> None:
    """
    Muestra estadísticas del sistema.

    Args:
        memory: Instancia de memoria.
    """
    stats = memory.get_statistics()

    print("\n" + "╭" + "─" * 78 + "╮")
    print("│" + " " * 26 + "📊 ESTADÍSTICAS DEL SISTEMA" + " " * 26 + "│")
    print("╰" + "─" * 78 + "╯")
    print(f"\n  📁 Total de snapshots guardados: {stats['total_snapshots']}")
    print(f"  🔔 Total de cambios detectados: {stats['total_changes']}")
    print(f"  🕐 Última verificación: {stats['last_check'] or 'Nunca'}")
    print(f"  📅 Primer snapshot: {stats['first_snapshot'] or 'N/A'}")

    if stats['total_changes'] > 0:
        print("\n  📝 Últimos 5 cambios:")
        recent = memory.get_recent_changes(5)
        print(memory.format_changes(recent))

    print("\n" + "╰" + "─" * 78 + "╯")


def export_data(memory: GradesMemory, filepath: str) -> None:
    """
    Exporta los datos a un archivo JSON.

    Args:
        memory: Instancia de memoria.
        filepath: Ruta del archivo de exportación.
    """
    try:
        memory.export_to_json(filepath)
        print(f"\n✅ Datos exportados exitosamente a: {filepath}")
    except StorageError as e:
        print(f"\n❌ Error al exportar: {e}")


def pretty_print_grades(grades_data: dict) -> None:
    """
    Muestra la información de calificaciones de forma tabular y legible.
    """
    alumno = grades_data.get('alumno', 'No disponible')
    matricula = grades_data.get('matricula', 'No disponible')
    periodo = grades_data.get('periodo', 'No disponible')
    fecha = grades_data.get('fecha_consulta', 'No disponible')

    # Detectar si matrícula parece no-numérica (hash u otro formato)
    matricula_note = ''
    if matricula and not matricula.isdigit():
        matricula_note = ' (posible hash/identificador no numérico)'

    # Header
    print('\n' + '═' * 90)
    print(f"🎓 Alumno: {alumno}")
    print(f"🆔 Matrícula: {matricula}{matricula_note}")
    print(f"📅 Periodo: {periodo}")
    print(f"⏱ Consulta: {fecha}")
    print('═' * 90 + '\n')

    # Tabla de materias
    headers = ["Clave", "Materia", "Profesor", "Grupo", "P1", "P2", "P3", "PF1", "PF2", "PF3", "Final"]
    col_widths = [8, 36, 20, 10, 6, 6, 6, 6, 6, 6, 7]

    # Imprimir encabezado de tabla
    def pad(text, width):
        txt = str(text) if text is not None else ''
        if len(txt) > width - 1:
            return txt[:width-3] + '...'
        return txt.ljust(width)

    header_line = ' '.join(pad(h, w) for h, w in zip(headers, col_widths))
    print(header_line)
    print('-' * sum(col_widths) + '-' * (len(col_widths) - 1))

    for materia in grades_data.get('materias', []):
        clave = materia.get('clave') or ''
        nombre = materia.get('nombre') or ''
        profesor = materia.get('profesor') or ''
        grupo = materia.get('grupo') or ''

        # Obtener calificaciones en orden P1..P3, PF1..PF3 y final
        def fmt(val):
            if val is None or val == '':
                return '--'
            try:
                # Mostrar con 2 decimales si es número
                return f"{float(val):.2f}"
            except Exception:
                return str(val)

        p1 = fmt(materia.get('calificaciones', {}).get('P1'))
        p2 = fmt(materia.get('calificaciones', {}).get('P2'))
        p3 = fmt(materia.get('calificaciones', {}).get('P3'))
        pf1 = fmt(materia.get('calificaciones_finales', {}) and materia.get('calificaciones_finales', {}).get('PF1'))
        pf2 = fmt(materia.get('calificaciones_finales', {}) and materia.get('calificaciones_finales', {}).get('PF2'))
        pf3 = fmt(materia.get('calificaciones_finales', {}) and materia.get('calificaciones_finales', {}).get('PF3'))
        final = materia.get('calificacion_final')
        final_str = fmt(final) if final is not None else '--'

        row = [clave, nombre, profesor, grupo, p1, p2, p3, pf1, pf2, pf3, final_str]
        print(' '.join(pad(c, w) for c, w in zip(row, col_widths)))

    print('\n' + '═' * 90 + '\n')


def main():
    """Función principal del programa."""
    # Parsear argumentos de línea de comandos
    parser = argparse.ArgumentParser(
        description="Sistema de Scraping de Calificaciones UPQ",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python main.py --get-grades          Obtener calificaciones actuales
  python main.py --check-new           Detectar nuevas calificaciones
  python main.py --export datos.json   Exportar historial completo
  python main.py --stats               Mostrar estadísticas
  python main.py --json                Mostrar calificaciones en JSON
        """
    )

    parser.add_argument(
        '--get-grades',
        action='store_true',
        help='Obtener calificaciones actuales y guardar snapshot'
    )

    parser.add_argument(
        '--check-new',
        action='store_true',
        help='Verificar si hay nuevas calificaciones desde el último check'
    )

    parser.add_argument(
        '--export',
        metavar='FILE',
        type=str,
        help='Exportar todos los datos a un archivo JSON'
    )

    parser.add_argument(
        '--stats',
        action='store_true',
        help='Mostrar estadísticas del sistema'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Mostrar calificaciones en formato JSON'
    )

    parser.add_argument(
        '--clear-history',
        action='store_true',
        help='Limpiar todo el historial (usar con precaución)'
    )

    args = parser.parse_args()

    # Si no se proporciona ningún argumento, mostrar ayuda
    if len(sys.argv) == 1:
        print_banner()
        parser.print_help()
        return

    # Imprimir banner
    print_banner()

    # Inicializar memoria
    try:
        memory = GradesMemory()
    except Exception as e:
        print(f"❌ Error al inicializar almacenamiento: {e}")
        sys.exit(1)

    # Manejar comandos que no requieren conexión
    if args.stats:
        show_statistics(memory)
        return

    if args.export:
        export_data(memory, args.export)
        return

    if args.clear_history:
        confirm = input("⚠️  ¿Estás seguro de que quieres limpiar el historial? (s/N): ")
        if confirm.lower() == 's':
            memory.clear_history()
            print("✅ Historial limpiado")
        else:
            print("❌ Operación cancelada")
        return

    # Comandos que requieren conexión al sistema UPQ
    if args.get_grades or args.check_new or args.json:
        # Validar configuración
        if not settings.validate():
            print("\n❌ Configura tus credenciales en el archivo .env")
            print("   Copia .env.example a .env y agrega tus datos")
            sys.exit(1)

        # Crear sesión y autenticar
        try:
            with UPQScraperSession() as session:
                print("\n╭────────────────────────────────────────────────────╮")
                print("│  🔐 Autenticando en el sistema UPQ..." + " " * 17 + "│")
                print("╰────────────────────────────────────────────────────╯")

                # Intentar login
                if not session.login():
                    print("\n❌ Error de autenticación")
                    sys.exit(1)

                # Ejecutar comando correspondiente
                if args.get_grades or args.json:
                    grades = get_grades(session, memory)

                    if grades:
                        if args.json:
                            # Mostrar en formato JSON
                            print("\n" + json.dumps(grades, indent=2, ensure_ascii=False))
                        else:
                            # Mostrar resumen legible (bonito)
                            pretty_print_grades(grades)

                        print("\n✅ Operación completada exitosamente")
                    else:
                        sys.exit(1)

                elif args.check_new:
                    check_new_grades(session, memory)
                    print("\n✅ Verificación completada")

        except AuthenticationError as e:
            print(f"\n❌ Error de autenticación: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n\n⚠️  Operación cancelada por el usuario")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ Error inesperado: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
