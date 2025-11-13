#!/usr/bin/env python3
"""
Sistema de Scraping de Calificaciones UPQ - Punto de entrada principal.

Uso:
    python main.py --get-grades      # Obtener calificaciones actuales
    python main.py --check-new       # Detectar nuevas calificaciones
    python main.py --export FILE     # Exportar datos a JSON
    python main.py --stats           # Mostrar estadísticas
    python main.py --info            # Información del perfil
    python main.py --promedio        # Promedio general
    python main.py --creditos        # Créditos y avance
    python main.py --estancias       # Estancias profesionales
    python main.py --historial       # Historial de promedios
    python main.py --horario         # Horario de clases
    python main.py --kardex          # Kardex académico
    python main.py --boleta          # Boleta de calificaciones
    python main.py --servicio        # Servicio social
    python main.py --perfil          # Perfil personal completo
    python main.py --pagos           # Historial de pagos
    python main.py --adeudos         # Adeudos pendientes
    python main.py --documentos      # Documentos escolares
    python main.py --calendario      # Calendario académico
"""

import argparse
import sys
import json
import os
from typing import Optional

# Configurar UTF-8 para Windows (para caracteres extendidos)
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
from bs4 import BeautifulSoup
import re


def print_banner():
    """Imprime el banner del sistema."""
    banner = """
+---------------------------------------------------------------+
|                                                               |
|  Sistema de Scraping de Calificaciones UPQ                    |
|                                                               |
|  Version: 1.0.0                                               |
|  Bot de Telegram integrado                                    |
|                                                               |
+---------------------------------------------------------------+
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
        # Obtener HTML de calificaciones y perfil del alumno (contiene nombre/matrícula)
        print("\n[INFO] Conectando al sistema UPQ...")
        grades_html = session.get_grades_html()

        # Intentar obtener la página home del alumno (contiene perfil completo)
        try:
            profile_html = session.get_home_data()
        except Exception:
            profile_html = ""
            try:
                # Fallback a alumnos.php solo para conservar nombre en "Bienvenido"
                profile_html = session.get_student_info()
            except Exception:
                profile_html = ""

        combined_html = profile_html + "\n" + grades_html

        # Guardar HTML para debug
        try:
            with open("debug_grades.html", "w", encoding="utf-8") as f:
                f.write(grades_html)
            if profile_html:
                with open("debug_profile.html", "w", encoding="utf-8") as f:
                    f.write(profile_html)
                print("[INFO] HTML de perfil guardado: debug_profile.html")
            print("[INFO] HTML de calificaciones guardado: debug_grades.html")
        except Exception:
            pass

        # Parsear HTML combinado
        print("[INFO] Extrayendo calificaciones...")
        parser = UPQGradesParser(combined_html)
        grades_data = parser.parse_grades()

        # Guardar snapshot
        memory.add_snapshot(grades_data)
        memory.save()

        return grades_data

    except FetchError as e:
        print(f"\n[ERROR] Error al obtener datos: {e}")
        return None
    except ParserError as e:
        print(f"\n[ERROR] Error al parsear HTML: {e}")
        print("   El formato del HTML puede haber cambiado")
        return None
    except Exception as e:
        print(f"\n[ERROR] Error inesperado: {e}")
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
        print("\n[ERROR] No se pudieron obtener las calificaciones actuales")
        return

    # Detectar cambios (se hace contra el penúltimo snapshot)
    # porque acabamos de agregar uno nuevo
    snapshots = memory.data.get("snapshots", [])

    if len(snapshots) < 2:
        print("\n[WARN] No hay snapshot previo para comparar")
        print("   Este es el primer snapshot guardado")
        print("\n[OK] Ejecuta --check-new nuevamente en el futuro para detectar cambios")
        return

    # Comparar con el penúltimo snapshot
    previous_snapshot = snapshots[-2]
    changes = memory.detect_changes(current_grades)

    # Guardar cambios
    memory.save()

    # Mostrar resultados
    print("\n" + "╭" + "─" * 78 + "╮")
    print("│" + " " * 25 + "RESULTADOS DE COMPARACIÓN" + " " * 25 + "│")
    print("╰" + "─" * 78 + "╯")

    if changes:
        print(f"\n[INFO] Se detectaron {len(changes)} cambios")
        print("\n" + memory.format_changes(changes))
    else:
        print("\n[OK] No hay cambios desde la última verificación")
        print(f"   Último check: {previous_snapshot['timestamp']}")


def show_statistics(memory: GradesMemory) -> None:
    """
    Muestra estadísticas del sistema.

    Args:
        memory: Instancia de memoria.
    """
    stats = memory.get_statistics()

    print("\n" + "╭" + "─" * 78 + "╮")
    print("│" + " " * 24 + "ESTADÍSTICAS DEL SISTEMA" + " " * 25 + "│")
    print("╰" + "─" * 78 + "╯")
    print(f"\n  Total de snapshots guardados: {stats['total_snapshots']}")
    print(f"  Total de cambios detectados: {stats['total_changes']}")
    print(f"  Última verificación: {stats['last_check'] or 'Nunca'}")
    print(f"  Primer snapshot: {stats['first_snapshot'] or 'N/A'}")

    if stats['total_changes'] > 0:
        print("\n  Últimos 5 cambios:")
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
        print(f"\n[OK] Datos exportados exitosamente a: {filepath}")
    except StorageError as e:
        print(f"\n[ERROR] Error al exportar: {e}")


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
    print(f"Alumno: {alumno}")
    print(f"Matrícula: {matricula}{matricula_note}")
    print(f"Periodo: {periodo}")
    print(f"Consulta: {fecha}")
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


def get_profile_info(session: UPQScraperSession) -> Optional[dict]:
    """Obtiene información del perfil del estudiante."""
    try:
        print("\n[INFO] Obteniendo información del perfil...")
        html = session.get_home_data()

        soup = BeautifulSoup(html, 'html.parser')
        profile_data = {}
        tables = soup.find_all('table')

        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all(['th', 'td'])
                if len(cols) >= 2:
                    key = cols[0].get_text(strip=True).lower()
                    value = cols[1].get_text(strip=True)

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
        print(f"\n[ERROR] Error al obtener perfil: {e}")
        return None


def show_profile_info(profile: dict) -> None:
    """Muestra la información del perfil."""
    print("\n" + "╭" + "─" * 78 + "╮")
    print("│" + " " * 22 + "INFORMACIÓN DEL PERFIL" + " " * 23 + "│")
    print("╰" + "─" * 78 + "╯\n")
    
    if 'nombre' in profile:
        print(f"  Nombre: {profile['nombre']}")
    if 'matricula' in profile:
        print(f"  Matrícula: {profile['matricula']}")
    if 'carrera' in profile:
        print(f"  Carrera: {profile['carrera']}")
    if 'cuatrimestre' in profile:
        print(f"  Cuatrimestre: {profile['cuatrimestre']}")
    if 'grupo' in profile:
        print(f"  Grupo: {profile['grupo']}")
    if 'generacion' in profile:
        print(f"  Generación: {profile['generacion']}")
    if 'promedio' in profile:
        print(f"  Promedio: {profile['promedio']}")
    if 'creditos' in profile:
        print(f"  Créditos: {profile['creditos']}")
    
    print("\n" + "╰" + "─" * 78 + "╯")


def show_promedio(session: UPQScraperSession) -> None:
    """Muestra el promedio general."""
    profile = get_profile_info(session)
    
    if not profile or 'promedio' not in profile:
        print("\n[ERROR] No se pudo obtener el promedio")
        return
    
    promedio = profile['promedio']
    print("\n" + "╭" + "─" * 78 + "╮")
    print("│" + " " * 27 + "PROMEDIO GENERAL" + " " * 32 + "│")
    print("╰" + "─" * 78 + "╯\n")
    print(f"  Tu promedio actual es: {promedio}\n")
    
    try:
        prom_num = float(promedio)
        if prom_num >= 9.0:
            print("  Excelente desempeño")
        elif prom_num >= 8.0:
            print("  Muy bien")
        elif prom_num >= 7.0:
            print("  Buen trabajo")
        else:
            print("  Sigue adelante")
    except:
        pass
    
    print("\n" + "╰" + "─" * 78 + "╯")


def show_creditos(session: UPQScraperSession) -> None:
    """Muestra información sobre créditos."""
    profile = get_profile_info(session)
    
    if not profile or 'creditos' not in profile:
        print("\n[ERROR] No se pudo obtener información de créditos")
        return
    
    creditos_text = profile['creditos']
    print("\n" + "╭" + "─" + "─" * 78 + "╮")
    print("│" + " " * 26 + "CRÉDITOS APROBADOS" + " " * 30 + "│")
    print("╰" + "─" * 78 + "╯\n")
    print(f"  {creditos_text}\n")
    
    if '/' in creditos_text:
        try:
            parts = creditos_text.split('/')
            aprobados = int(parts[0].strip())
            totales = int(parts[1].strip().split()[0])
            porcentaje = (aprobados / totales) * 100
            faltantes = totales - aprobados
            
            print(f"  Avance: {porcentaje:.1f}%")
            print(f"  Te faltan: {faltantes} créditos\n")

            if porcentaje >= 90:
                print("  Casi listo para graduarte")
            elif porcentaje >= 75:
                print("  Ya estás en la recta final")
            elif porcentaje >= 50:
                print("  Vas por buen camino")
            else:
                print("  Sigue adelante")
        except:
            pass
    
    print("\n" + "╰" + "─" * 78 + "╯")


def show_estancias(session: UPQScraperSession) -> None:
    """Muestra información de estancias profesionales."""
    try:
        from scraper.parser import parse_estancias
        
        print("\n[INFO] Obteniendo información de estancias...")
        html = session.get_info_general()
        
        # Guardar debug
        with open("debug_estancias_main.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        estancias = parse_estancias(html)
        
        if not estancias:
            print("\n[INFO] No se encontraron estancias registradas")
            return
        
        print("\n" + "╭" + "─" * 78 + "╮")
        print("│" + " " * 24 + "ESTANCIAS PROFESIONALES" + " " * 28 + "│")
        print("╰" + "─" * 78 + "╯\n")
        
        for estancia in estancias:
            numero = estancia.get('numero', '?')
            curso = estancia.get('curso', 'N/A')
            empresa = estancia.get('empresa', 'N/A')
            periodo = estancia.get('periodo', 'N/A')
            estatus = estancia.get('estatus', 'N/A')
            descripcion = estancia.get('descripcion', '')
            
            if estatus == "CONCLUIDO":
                estado = "[OK]"
            elif estatus == "AUTORIZADO":
                estado = "[PENDIENTE]"
            else:
                estado = "[INFO]"

            print(f"  {estado} {curso}")
            print(f"     Empresa: {empresa}")
            print(f"     Periodo: {periodo}")
            print(f"     Estatus: {estatus}")
            
            if descripcion:
                # Mostrar solo los primeros 100 caracteres de la descripción
                desc_corta = descripcion[:100] + "..." if len(descripcion) > 100 else descripcion
                print(f"     Descripción: {desc_corta}")
            
            print()
        
        print("╰" + "─" * 78 + "╯")
        
    except Exception as e:
        print(f"\n[ERROR] Error al obtener estancias: {e}")
        import traceback
        traceback.print_exc()


def show_historial_promedios(session: UPQScraperSession) -> None:
    """Muestra el historial de promedios por cuatrimestre."""
    try:
        print("\n[INFO] Obteniendo historial de promedios...")
        html = session.get_info_general()
        
        soup = BeautifulSoup(html, 'html.parser')
        historial = []
        
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
                                
                                if re.search(r'\d+', cuatrimestre):
                                    historial.append({
                                        'cuatrimestre': cuatrimestre,
                                        'promedio': promedio
                                    })
        
        if not historial:
            print("\n[INFO] No se encontró historial de promedios")
            return
        
        print("\n" + "╭" + "─" * 78 + "╮")
        print("│" + " " * 26 + "HISTORIAL DE PROMEDIOS" + " " * 29 + "│")
        print("╰" + "─" * 78 + "╯\n")
        
        for item in historial:
            print(f"  {item['cuatrimestre']}: {item['promedio']}")
        
        print("\n" + "╰" + "─" * 78 + "╯")
        
    except Exception as e:
        print(f"\n[ERROR] Error al obtener historial: {e}")


def show_horario(session: UPQScraperSession) -> None:
    """Muestra el horario de clases."""
    try:
        print("\n[INFO] Obteniendo horario de clases...")
        html = session.get_horario()
        
        soup = BeautifulSoup(html, 'html.parser')
        
        print("\n" + "╭" + "─" * 78 + "╮")
        print("│" + " " * 28 + "HORARIO DE CLASES" + " " * 31 + "│")
        print("╰" + "─" * 78 + "╯\n")
        
        # Buscar tabla de horario
        tables = soup.find_all('table')
        found = False
        
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) > 0:
                found = True
                for row in rows:
                    cols = row.find_all(['th', 'td'])
                    if cols:
                        row_text = " | ".join([col.get_text(strip=True) for col in cols])
                        print(f"  {row_text}")
        
        if not found:
            print("  No se encontró información de horario")
        
        print("\n" + "╰" + "─" * 78 + "╯")
        
    except Exception as e:
        print(f"\n[ERROR] Error al obtener horario: {e}")


def show_kardex(session: UPQScraperSession) -> None:
    """Muestra el kardex académico completo."""
    try:
        from scraper.parser import parse_kardex

        print("\n[INFO] Obteniendo kardex académico...")
        html = session.get_kardex()
        
        # Guardar debug
        with open("debug_kardex_main.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        materias = parse_kardex(html)
        
        if not materias:
            print("\n[INFO] No se encontró información del kardex")
            return
        
        print("\n" + "╭" + "─" * 78 + "╮")
        print("│" + " " * 28 + "KARDEX ACADÉMICO" + " " * 32 + "│")
        print("╰" + "─" * 78 + "╯\n")
        
        cuatrimestre_actual = None
        for materia in materias:
            cuatri = materia.get('cuatrimestre', 'N/A')
            
            # Encabezado de cuatrimestre
            if cuatri != cuatrimestre_actual:
                if cuatrimestre_actual is not None:
                    print()
                print(f"  ━━ Cuatrimestre {cuatri} ━━")
                cuatrimestre_actual = cuatri
            
            # Información de materia
            nombre = materia.get('materia', 'N/A')
            cal = materia.get('calificacion', 'N/A')
            tipo = materia.get('tipo_evaluacion', 'N/A')
            
            try:
                cal_num = float(cal)
                indicador = "[APROBADA]" if cal_num >= 7 else "[NO ACREDITADA]"
            except:
                indicador = "[SIN DATOS]"

            print(f"  {indicador} {nombre}: {cal}")
            print(f"     Tipo de evaluación: {tipo}")
        
        print(f"\n  Total: {len(materias)} materias cursadas")
        print("\n" + "╰" + "─" * 78 + "╯")
        
    except Exception as e:
        print(f"\n[ERROR] Error al obtener kardex: {e}")
        import traceback
        traceback.print_exc()


def show_boleta(session: UPQScraperSession) -> None:
    """Muestra la boleta de calificaciones."""
    try:
        print("\n[INFO] Obteniendo boleta de calificaciones...")
        html = session.get_boleta()
        
        soup = BeautifulSoup(html, 'html.parser')
        
        print("\n" + "╭" + "─" * 78 + "╮")
        print("│" + " " * 25 + "BOLETA DE CALIFICACIONES" + " " * 28 + "│")
        print("╰" + "─" * 78 + "╯\n")
        
        # Buscar tabla de boleta
        tables = soup.find_all('table')
        found = False
        
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) > 0:
                found = True
                for row in rows:
                    cols = row.find_all(['th', 'td'])
                    if cols:
                        row_text = " | ".join([col.get_text(strip=True) for col in cols])
                        print(f"  {row_text}")
        
        if not found:
            print("  No se encontró boleta de calificaciones")
        
        print("\n" + "╰" + "─" * 78 + "╯")
        
    except Exception as e:
        print(f"\n[ERROR] Error al obtener boleta: {e}")


def show_servicio_social(session: UPQScraperSession) -> None:
    """Muestra información del servicio social."""
    try:
        from scraper.parser import parse_servicio_social

        print("\n[INFO] Obteniendo información de servicio social...")
        html = session.get_info_general()
        
        # Guardar debug
        with open("debug_servicio_main.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        servicio = parse_servicio_social(html)
        
        if not servicio:
            print("\n[INFO] No se encontró información del servicio social")
            return
        
        print("\n" + "╭" + "─" * 78 + "╮")
        print("│" + " " * 28 + "SERVICIO SOCIAL" + " " * 35 + "│")
        print("╰" + "─" * 78 + "╯\n")
        
        # Estado del servicio
        activo = servicio.get('activo', False)
        if activo:
            print("  [OK] Servicio social ACTIVO\n")
        else:
            print("  [INFO] Servicio social NO ACTIVO\n")
        
        # Requisitos
        mat_req = servicio.get('materias_requeridas', 'N/A')
        mat_falt = servicio.get('materias_faltantes', 'N/A')
        
        print(f"  Materias requeridas: {mat_req}")
        print(f"  Materias faltantes: {mat_falt}\n")
        
        # Estatus
        estatus = servicio.get('estatus', 'N/A')
        cumple = servicio.get('cumple_requisitos', False)
        
        if cumple:
            print(f"  [OK] {estatus}")
            print("  Puedes comenzar tu servicio social")
        else:
            print(f"  [WARN] {estatus}")
            if mat_falt != 'N/A':
                print(f"  Te faltan {mat_falt} materias para cumplir requisitos.")
        
        print("\n" + "╰" + "─" * 78 + "╯")
        
    except Exception as e:
        print(f"\n[ERROR] Error al obtener servicio social: {e}")
        import traceback
        traceback.print_exc()


def show_perfil_personal(session: UPQScraperSession) -> None:
    """Muestra el perfil personal completo."""
    try:
        from scraper.parser import parse_student_profile
        
        print("\n[INFO] Obteniendo perfil personal...")
        html = session.get_perfil()
        
        # Guardar debug
        with open("debug_perfil_main.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        perfil = parse_student_profile(html)
        
        if not perfil:
            print("\n[INFO] No se encontró información del perfil")
            return
        
        print("\n" + "╭" + "─" * 78 + "╮")
        print("│" + " " * 27 + "PERFIL PERSONAL" + " " * 35 + "│")
        print("╰" + "─" * 78 + "╯\n")
        
        # Función helper para obtener campos
        def get_field(key1, key2='', default='N/A'):
            return perfil.get(key1, perfil.get(key2, default))
        
        # Datos personales
        nombre = get_field('nombre')
        matricula = get_field('matrícula', 'matricula')
        carrera = get_field('carrera')
        generacion = get_field('generación', 'generacion')
        grupo = get_field('grupo')
        
        print("  DATOS PERSONALES")
        print(f"     Nombre: {nombre}")
        print(f"     Matrícula: {matricula}")
        print(f"     NSS: {get_field('nss')}")
        print()
        
        # Datos académicos
        cuatrimestre = get_field('último_cuatrimestre', 'ultimo_cuatrimestre')
        promedio = get_field('promedio_general')
        materias_aprob = get_field('materias_aprobadas')
        materias_no_acred = get_field('materias_no_acreditadas')
        creditos = get_field('créditos_aprobados', 'creditos_aprobados')
        nivel_ingles = get_field('nivel_inglés', 'nivel_ingles')
        estatus = get_field('estatus_actual', 'estatus')
        
        print("  DATOS ACADÉMICOS")
        print(f"     Carrera: {carrera}")
        print(f"     Generación: {generacion}")
        print(f"     Grupo: {grupo}")
        print(f"     Cuatrimestre: {cuatrimestre}")
        print(f"     Estatus: {estatus}")
        print()
        
        print("  DESEMPEÑO")
        print(f"     Promedio: {promedio}")
        print(f"     Materias Aprobadas: {materias_aprob}")
        print(f"     Materias No Acreditadas: {materias_no_acred}")
        print(f"     Créditos Aprobados: {creditos}")
        print(f"     Nivel Inglés: {nivel_ingles}")
        print()
        
        # Tutoría
        tutor = get_field('tutores', 'tutor')
        email_tutor = get_field('correo_tutor', 'email_tutor')
        
        print("  TUTORÍA")
        print(f"     Tutor: {tutor}")
        print(f"     Email: {email_tutor}")
        
        print("\n" + "╰" + "─" * 78 + "╯")

    except Exception as e:
        print(f"\n[ERROR] Error al obtener perfil: {e}")
        import traceback
        traceback.print_exc()


def show_pagos(session: UPQScraperSession) -> None:
    """Muestra el historial de pagos."""
    try:
        print("\n[INFO] Obteniendo historial de pagos...")
        html = session.get_pagos()
        
        soup = BeautifulSoup(html, 'html.parser')
        
        print("\n" + "╭" + "─" * 78 + "╮")
        print("│" + " " * 27 + "HISTORIAL DE PAGOS" + " " * 32 + "│")
        print("╰" + "─" * 78 + "╯\n")
        
        # Buscar tabla de pagos
        tables = soup.find_all('table')
        found = False
        
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) > 0:
                found = True
                for row in rows:
                    cols = row.find_all(['th', 'td'])
                    if cols:
                        row_text = " | ".join([col.get_text(strip=True) for col in cols])
                        print(f"  {row_text}")
        
        if not found:
            print("  [INFO] No se encontró historial de pagos")
        
        print("\n" + "╰" + "─" * 78 + "╯")
        
    except Exception as e:
        print(f"\n[ERROR] Error al obtener pagos: {e}")


def show_adeudos(session: UPQScraperSession) -> None:
    """Muestra los adeudos pendientes."""
    try:
        print("\n[INFO] Obteniendo adeudos...")
        html = session.get_adeudos()
        
        soup = BeautifulSoup(html, 'html.parser')
        
        print("\n" + "╭" + "─" * 78 + "╮")
        print("│" + " " * 30 + "ADEUDOS PENDIENTES" + " " * 30 + "│")
        print("╰" + "─" * 78 + "╯\n")
        
        # Buscar tabla de adeudos
        tables = soup.find_all('table')
        found = False
        
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) > 0:
                found = True
                for row in rows:
                    cols = row.find_all(['th', 'td'])
                    if cols:
                        row_text = " | ".join([col.get_text(strip=True) for col in cols])
                        print(f"  {row_text}")
        
        if not found:
            print("  [OK] No se encontraron adeudos pendientes")
        
        print("\n" + "╰" + "─" * 78 + "╯")
        
    except Exception as e:
        print(f"\n[ERROR] Error al obtener adeudos: {e}")


def show_documentos(session: UPQScraperSession) -> None:
    """Muestra los documentos escolares disponibles."""
    try:
        print("\n[INFO] Obteniendo documentos escolares...")
        html = session.get_documentos()
        
        soup = BeautifulSoup(html, 'html.parser')
        
        print("\n" + "╭" + "─" * 78 + "╮")
        print("│" + " " * 26 + "DOCUMENTOS ESCOLARES" + " " * 30 + "│")
        print("╰" + "─" * 78 + "╯\n")
        
        # Buscar documentos disponibles
        documentos = []
        links = soup.find_all('a')
        
        for link in links:
            text = link.get_text(strip=True)
            href = link.get('href', '')
            if text and ('pdf' in href.lower() or 'documento' in text.lower() or 'constancia' in text.lower()):
                documentos.append({'nombre': text, 'url': href})
        
        if documentos:
            for doc in documentos:
                print(f"  Documento: {doc['nombre']}")
                if doc['url']:
                    print(f"     Enlace: {doc['url']}")
        else:
            print("  [INFO] No se encontraron documentos disponibles")
        
        print("\n" + "╰" + "─" * 78 + "╯")
        
    except Exception as e:
        print(f"\n[ERROR] Error al obtener documentos: {e}")


def show_calendario(session: UPQScraperSession) -> None:
    """Muestra el calendario académico."""
    try:
        print("\n[INFO] Obteniendo calendario académico...")
        html = session.get_calendario()
        
        soup = BeautifulSoup(html, 'html.parser')
        
        print("\n" + "╭" + "─" * 78 + "╮")
        print("│" + " " * 27 + "CALENDARIO ACADÉMICO" + " " * 30 + "│")
        print("╰" + "─" * 78 + "╯\n")
        
        # Buscar tabla de calendario
        tables = soup.find_all('table')
        found = False
        
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) > 0:
                found = True
                for row in rows:
                    cols = row.find_all(['th', 'td'])
                    if cols:
                        row_text = " | ".join([col.get_text(strip=True) for col in cols])
                        print(f"  {row_text}")
        
        if not found:
            print("  [INFO] No se encontró calendario académico")
        
        print("\n" + "╰" + "─" * 78 + "╯")
        
    except Exception as e:
        print(f"\n[ERROR] Error al obtener calendario: {e}")


def show_historial_promedios(session: UPQScraperSession) -> None:
    """Muestra el historial de promedios por cuatrimestre."""
    try:
        print("\n[INFO] Obteniendo historial de promedios...")
        html = session.get_info_general()
        
        soup = BeautifulSoup(html, 'html.parser')
        historial = []
        
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
                                
                                if re.search(r'\d+', cuatrimestre):
                                    historial.append({
                                        'cuatrimestre': cuatrimestre,
                                        'promedio': promedio
                                    })
        
        if not historial:
            print("\n[INFO] No se encontró historial de promedios")
            return
        
        print("\n" + "╭" + "─" * 78 + "╮")
        print("│" + " " * 25 + "HISTORIAL DE PROMEDIOS" + " " * 30 + "│")
        print("╰" + "─" * 78 + "╯\n")
        
        for item in historial:
            print(f"  {item['cuatrimestre']}: {item['promedio']}")
        
        print("\n  Consejo: Analiza tu evolución para identificar patrones")
        print("\n" + "╰" + "─" * 78 + "╯")
        
    except Exception as e:
        print(f"\n[ERROR] Error al obtener historial: {e}")


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

    parser.add_argument(
        '--info',
        action='store_true',
        help='Mostrar información del perfil del estudiante'
    )

    parser.add_argument(
        '--promedio',
        action='store_true',
        help='Mostrar promedio general'
    )

    parser.add_argument(
        '--creditos',
        action='store_true',
        help='Mostrar créditos aprobados y avance'
    )

    parser.add_argument(
        '--estancias',
        action='store_true',
        help='Mostrar información de estancias profesionales'
    )

    parser.add_argument(
        '--historial',
        action='store_true',
        help='Mostrar historial de promedios por cuatrimestre'
    )
    
    parser.add_argument(
        '--horario',
        action='store_true',
        help='Mostrar horario de clases'
    )
    
    parser.add_argument(
        '--kardex',
        action='store_true',
        help='Mostrar kardex académico completo'
    )
    
    parser.add_argument(
        '--boleta',
        action='store_true',
        help='Mostrar boleta de calificaciones'
    )
    
    parser.add_argument(
        '--servicio',
        action='store_true',
        help='Mostrar información del servicio social'
    )
    
    parser.add_argument(
        '--perfil',
        action='store_true',
        help='Mostrar perfil personal completo'
    )
    
    parser.add_argument(
        '--pagos',
        action='store_true',
        help='Mostrar historial de pagos'
    )
    
    parser.add_argument(
        '--adeudos',
        action='store_true',
        help='Mostrar adeudos pendientes'
    )
    
    parser.add_argument(
        '--documentos',
        action='store_true',
        help='Mostrar documentos escolares disponibles'
    )
    
    parser.add_argument(
        '--calendario',
        action='store_true',
        help='Mostrar calendario académico'
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
        print(f"[ERROR] Error al inicializar almacenamiento: {e}")
        sys.exit(1)

    # Manejar comandos que no requieren conexión
    if args.stats:
        show_statistics(memory)
        return

    if args.export:
        export_data(memory, args.export)
        return

    if args.clear_history:
        confirm = input("[WARN] ¿Estás seguro de que quieres limpiar el historial? (s/N): ")
        if confirm.lower() == 's':
            memory.clear_history()
            print("[OK] Historial limpiado")
        else:
            print("[INFO] Operación cancelada")
        return

    # Comandos que requieren conexión al sistema UPQ
    if (args.get_grades or args.check_new or args.json or args.info or args.promedio or 
        args.creditos or args.estancias or args.historial or args.horario or args.kardex or 
        args.boleta or args.servicio or args.perfil or args.pagos or args.adeudos or 
        args.documentos or args.calendario):
        # Validar configuración
        if not settings.validate():
            print("\n[ERROR] Configura tus credenciales en el archivo .env")
            print("   Copia .env.example a .env y agrega tus datos")
            sys.exit(1)

        # Crear sesión y autenticar
        try:
            with UPQScraperSession() as session:
                print("\n╭────────────────────────────────────────────────────╮")
                print("│  Autenticando en el sistema UPQ..." + " " * 23 + "│")
                print("╰────────────────────────────────────────────────────╯")

                # Intentar login
                if not session.login():
                    print("\n[ERROR] Error de autenticación")
                    sys.exit(1)

                # Ejecutar comando correspondiente
                if args.info:
                    profile = get_profile_info(session)
                    if profile:
                        show_profile_info(profile)
                        print("\n[OK] Operación completada exitosamente")
                    else:
                        sys.exit(1)
                
                elif args.promedio:
                    show_promedio(session)
                    print("\n[OK] Operación completada exitosamente")
                
                elif args.creditos:
                    show_creditos(session)
                    print("\n[OK] Operación completada exitosamente")
                
                elif args.estancias:
                    show_estancias(session)
                    print("\n[OK] Operación completada exitosamente")
                
                elif args.historial:
                    show_historial_promedios(session)
                    print("\n[OK] Operación completada exitosamente")
                
                elif args.horario:
                    show_horario(session)
                    print("\n[OK] Operación completada exitosamente")
                
                elif args.kardex:
                    show_kardex(session)
                    print("\n[OK] Operación completada exitosamente")
                
                elif args.boleta:
                    show_boleta(session)
                    print("\n[OK] Operación completada exitosamente")
                
                elif args.servicio:
                    show_servicio_social(session)
                    print("\n[OK] Operación completada exitosamente")
                
                elif args.perfil:
                    show_perfil_personal(session)
                    print("\n[OK] Operación completada exitosamente")
                
                elif args.pagos:
                    show_pagos(session)
                    print("\n[OK] Operación completada exitosamente")
                
                elif args.adeudos:
                    show_adeudos(session)
                    print("\n[OK] Operación completada exitosamente")
                
                elif args.documentos:
                    show_documentos(session)
                    print("\n[OK] Operación completada exitosamente")
                
                elif args.calendario:
                    show_calendario(session)
                    print("\n[OK] Operación completada exitosamente")
                
                elif args.get_grades or args.json:
                    grades = get_grades(session, memory)

                    if grades:
                        if args.json:
                            # Mostrar en formato JSON
                            print("\n" + json.dumps(grades, indent=2, ensure_ascii=False))
                        else:
                            # Mostrar resumen legible (bonito)
                            pretty_print_grades(grades)

                        print("\n[OK] Operación completada exitosamente")
                    else:
                        sys.exit(1)

                elif args.check_new:
                    check_new_grades(session, memory)
                    print("\n[OK] Verificación completada")

        except AuthenticationError as e:
            print(f"\n[ERROR] Error de autenticación: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n\n[WARN] Operación cancelada por el usuario")
            sys.exit(0)
        except Exception as e:
            print(f"\n[ERROR] Error inesperado: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
