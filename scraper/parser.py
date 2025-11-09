"""
Módulo para parsear HTML del sistema UPQ.
Implementa parseo robusto que funciona incluso si cambian estilos CSS.
"""

from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
import re
from datetime import datetime


class ParserError(Exception):
    """Error al parsear HTML."""
    pass


class UPQGradesParser:
    """
    Parser robusto para extraer calificaciones del HTML del sistema UPQ.
    No depende de clases CSS o IDs, solo de estructura semántica y contenido.
    """

    def __init__(self, html: str):
        """
        Inicializa el parser con HTML.

        Args:
            html: HTML de la página de calificaciones.
        """
        self.html = html
        self.soup = BeautifulSoup(html, 'html.parser')

    def parse_grades(self) -> Dict[str, Any]:
        """
        Parsea el HTML y extrae todas las calificaciones.

        Returns:
            Dict con estructura:
            {
                "alumno": str,
                "matricula": str,
                "periodo": str,
                "fecha_consulta": str (ISO format),
                "materias": List[Dict]
            }

        Raises:
            ParserError: Si no se puede parsear el HTML.
        """
        try:
            print("🔍 Parseando HTML de calificaciones...")

            # Extraer información del alumno
            student_info = self._extract_student_info()

            # Extraer tabla de calificaciones
            grades_table = self._find_grades_table()

            if not grades_table:
                raise ParserError(
                    "No se encontró la tabla de calificaciones en el HTML"
                )

            # Parsear la tabla
            materias = self._parse_grades_table(grades_table)

            result = {
                "alumno": student_info.get("nombre", "No disponible"),
                "matricula": student_info.get("matricula", "No disponible"),
                "periodo": student_info.get("periodo", "No disponible"),
                "fecha_consulta": datetime.now().isoformat(),
                "materias": materias
            }

            print(f"✅ Parseadas {len(materias)} materias exitosamente")

            return result

        except Exception as e:
            raise ParserError(f"Error al parsear calificaciones: {str(e)}")

    def _extract_student_info(self) -> Dict[str, str]:
        """
        Extrae información del alumno del HTML.

        Returns:
            Dict con nombre, matrícula y periodo si están disponibles.
        """
        info = {}

        # Buscar matrícula con múltiples patrones
        for pattern in [
            r'Matrícula:\s*(\d{8,9})',
            r'Matricula:\s*(\d{8,9})',
            r'MATRÍCULA:\s*(\d{8,9})',
            r'MATRICULA:\s*(\d{8,9})',
            r'Cuenta:\s*(\d{8,9})',
            r'No\.\s*Control:\s*(\d{8,9})',
            r'\b(\d{8,9})\b'  # Fallback: cualquier número de 8-9 dígitos
        ]:
            match = re.search(pattern, self.html, re.IGNORECASE)
            if match:
                info["matricula"] = match.group(1)
                break

        # Buscar nombre del alumno (puede estar en varios lugares)
        # Buscamos patrones comunes
        for pattern in [
            r'Bienvenido\s+([A-ZÁÉÍÓÚÑ\s]+)',  # Patrón "Bienvenido NOMBRE"
            r'Alumno:\s*([A-ZÁÉÍÓÚÑ\s]+)',
            r'Nombre:\s*([A-ZÁÉÍÓÚÑ\s]+)',
            r'ALUMNO:\s*([A-ZÁÉÍÓÚÑ\s]+)',
            r'NOMBRE:\s*([A-ZÁÉÍÓÚÑ\s]+)',
            r'Estudiante:\s*([A-ZÁÉÍÓÚÑ\s]+)',
            # Buscar en elementos HTML específicos
        ]:
            match = re.search(pattern, self.html, re.IGNORECASE)
            if match:
                nombre = match.group(1).strip()
                # Limpiar el nombre (remover múltiples espacios)
                nombre = re.sub(r'\s+', ' ', nombre)
                # Solo aceptar si tiene al menos 2 palabras (nombre y apellido)
                if len(nombre.split()) >= 2:
                    info["nombre"] = nombre
                    break
        
        # Si no encontramos con regex, buscar en elementos HTML
        if "nombre" not in info:
            # Buscar en divs, spans, h1-h6 que contengan "Bienvenido" o "Alumno"
            for tag in self.soup.find_all(['div', 'span', 'h1', 'h2', 'h3', 'h4', 'p']):
                text = tag.get_text(strip=True)
                if 'Bienvenido' in text or 'bienvenido' in text:
                    # Extraer el nombre después de "Bienvenido"
                    match = re.search(r'[Bb]ienvenido\s+([A-ZÁÉÍÓÚÑ\s]+)', text)
                    if match:
                        nombre = match.group(1).strip()
                        nombre = re.sub(r'\s+', ' ', nombre)
                        if len(nombre.split()) >= 2:
                            info["nombre"] = nombre
                            break

        # Buscar periodo académico
        for pattern in [
            r'Periodo:\s*([A-Z\s\-\d]+)',
            r'PERIODO:\s*([A-Z\s\-\d]+)',
            r'(ENERO-ABRIL|MAYO-AGOSTO|SEPTIEMBRE-DICIEMBRE)\s*\d{4}'
        ]:
            match = re.search(pattern, self.html)
            if match:
                info["periodo"] = match.group(1).strip()
                break

        return info

    def _find_grades_table(self) -> Optional[Any]:
        """
        Encuentra la tabla de calificaciones en el HTML.
        Busca de forma robusta sin depender de IDs o clases.

        Returns:
            Tag de BeautifulSoup con la tabla, o None si no se encuentra.
        """
        # Estrategia 1: Buscar tabla con headers que contengan palabras clave
        tables = self.soup.find_all('table')

        for table in tables:
            # Buscar headers en la tabla
            headers = table.find_all('th')
            header_texts = [th.get_text(strip=True).lower() for th in headers]

            # Si contiene palabras clave relacionadas con calificaciones
            keywords = ['materia', 'calificación', 'parcial', 'p1', 'p2', 'p3', 'grupo', 'profesor']
            if any(keyword in ' '.join(header_texts) for keyword in keywords):
                return table

        # Estrategia 2: Buscar la tabla más grande con <td> y <tr>
        if tables:
            largest_table = max(tables, key=lambda t: len(t.find_all('tr')))
            if len(largest_table.find_all('tr')) > 1:
                return largest_table

        return None

    def _parse_grades_table(self, table: Any) -> List[Dict[str, Any]]:
        """
        Parsea la tabla de calificaciones.

        Args:
            table: Tag de BeautifulSoup con la tabla.

        Returns:
            Lista de diccionarios con información de cada materia.
        """
        materias = []

        # Extraer headers - buscar la fila de headers real (sin colspan)
        # El sistema UPQ tiene 2 filas de headers: una de agrupación y una real
        thead = table.find('thead')
        header_row = None

        if thead:
            # Buscar todas las filas de headers
            header_rows = thead.find_all('tr')
            # Usar la última fila (que tiene los headers detallados sin colspan)
            for row in reversed(header_rows):
                headers = row.find_all('th')
                # Verificar que no todos los headers tengan colspan
                has_colspan = any(h.get('colspan') for h in headers)
                if not has_colspan or len(headers) > 5:
                    header_row = row
                    break

        if not header_row:
            # Fallback: buscar cualquier fila con <th>
            header_row = table.find('tr')

        headers = header_row.find_all('th') if header_row else []
        if not headers:
            headers = header_row.find_all(['th', 'td']) if header_row else []

        header_texts = [h.get_text(strip=True) for h in headers]

        # Mapear índices de columnas importantes
        column_map = self._map_columns(header_texts)

        # Extraer filas de datos
        rows = table.find_all('tr')

        for row in rows:
            cells = row.find_all('td')

            # Saltar filas sin suficientes celdas (mínimo 2: materia + algo)
            if len(cells) < 2:
                continue

            # Extraer datos de la materia
            materia = self._extract_materia_data(cells, column_map)

            if materia and materia.get('nombre'):
                materias.append(materia)

        return materias

    def _map_columns(self, headers: List[str]) -> Dict[str, int]:
        """
        Mapea los nombres de columnas a sus índices.
        Hace matching flexible por contenido, no por nombres exactos.

        Args:
            headers: Lista de nombres de headers.

        Returns:
            Diccionario mapeando tipo de columna a índice.
        """
        column_map = {}

        for i, header in enumerate(headers):
            header_lower = header.lower()

            # Materia / Asignatura
            if any(word in header_lower for word in ['materia', 'asignatura', 'curso']):
                column_map['materia'] = i

            # Clave
            elif any(word in header_lower for word in ['clave', 'código', 'codigo']):
                column_map['clave'] = i

            # Aula
            elif any(word in header_lower for word in ['aula', 'salón', 'salon']):
                column_map['aula'] = i

            # Grupo
            elif any(word in header_lower for word in ['grupo', 'sección', 'seccion']):
                column_map['grupo'] = i

            # Profesor
            elif any(word in header_lower for word in ['profesor', 'docente', 'maestro']):
                column_map['profesor'] = i

            # Calificaciones por parcial (P1, P2, P3, etc.)
            elif re.search(r'p[1-9]|pf[1-9]|primer|segundo|tercer|parcial', header_lower):
                # Detectar número de parcial
                parcial_num = self._extract_parcial_number(header_lower)
                if parcial_num:
                    # Detectar si es parcial final (PF)
                    if 'pf' in header_lower or 'final del' in header_lower:
                        column_map[f'PF{parcial_num}'] = i
                    else:
                        column_map[f'P{parcial_num}'] = i

            # Calificación Final (promedio final)
            elif 'final' in header_lower and 'calificación' in header_lower:
                column_map['calificacion_final'] = i

        return column_map

    def _extract_parcial_number(self, text: str) -> Optional[int]:
        """
        Extrae el número de parcial de un texto.

        Args:
            text: Texto del header.

        Returns:
            Número de parcial (1, 2, 3, etc.) o None.
        """
        # Buscar P1, P2, P3, etc.
        match = re.search(r'p(\d)', text.lower())
        if match:
            return int(match.group(1))

        # Buscar "primer", "segundo", "tercer"
        ordinals = {
            'primer': 1, 'segundo': 2, 'tercer': 3,
            'cuarto': 4, 'quinto': 5, 'sexto': 6
        }
        for word, num in ordinals.items():
            if word in text.lower():
                return num

        return None

    def _extract_materia_data(
        self,
        cells: List[Any],
        column_map: Dict[str, int]
    ) -> Optional[Dict[str, Any]]:
        """
        Extrae datos de una materia desde las celdas de una fila.

        Args:
            cells: Lista de celdas (<td>) de la fila.
            column_map: Mapeo de columnas a índices.

        Returns:
            Diccionario con datos de la materia o None si no es válido.
        """
        try:
            # Obtener valor de celda de forma segura
            def get_cell_value(col_name: str) -> Optional[str]:
                if col_name in column_map and column_map[col_name] < len(cells):
                    value = cells[column_map[col_name]].get_text(strip=True)
                    return value if value else None
                return None

            # Extraer nombre de materia (campo obligatorio)
            nombre = get_cell_value('materia')
            if not nombre or len(nombre) < 3:
                return None

            # Extraer calificaciones parciales (P1, P2, P3)
            calificaciones = {}
            for i in range(1, 10):  # Buscar hasta P9
                parcial = f'P{i}'
                if parcial in column_map:
                    valor = get_cell_value(parcial)
                    if valor:
                        # Intentar convertir a float
                        try:
                            calificaciones[parcial] = float(valor)
                        except ValueError:
                            # Si no es número, dejarlo como None
                            calificaciones[parcial] = None
                    else:
                        calificaciones[parcial] = None

            # Extraer calificaciones finales de parciales (PF1, PF2, PF3)
            calificaciones_finales = {}
            for i in range(1, 10):
                parcial_final = f'PF{i}'
                if parcial_final in column_map:
                    valor = get_cell_value(parcial_final)
                    if valor:
                        try:
                            calificaciones_finales[parcial_final] = float(valor)
                        except ValueError:
                            calificaciones_finales[parcial_final] = None
                    else:
                        calificaciones_finales[parcial_final] = None

            # Extraer calificación final de la materia
            calif_final = get_cell_value('calificacion_final')
            calif_final_valor = None
            if calif_final:
                try:
                    calif_final_valor = float(calif_final)
                except ValueError:
                    pass

            materia_data = {
                "nombre": nombre,
                "clave": get_cell_value('clave'),
                "aula": get_cell_value('aula'),
                "grupo": get_cell_value('grupo'),
                "profesor": get_cell_value('profesor'),
                "calificaciones": calificaciones,
                "calificaciones_finales": calificaciones_finales if calificaciones_finales else None,
                "calificacion_final": calif_final_valor
            }

            return materia_data

        except Exception as e:
            print(f"⚠️  Error al parsear fila: {str(e)}")
            return None

    def get_raw_html(self) -> str:
        """Retorna el HTML original."""
        return self.html

    def save_html_debug(self, filepath: str) -> None:
        """
        Guarda el HTML para debugging.

        Args:
            filepath: Ruta donde guardar el HTML.
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.html)
        print(f"💾 HTML guardado para debugging en: {filepath}")
