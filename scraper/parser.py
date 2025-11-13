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
            print("[INFO] Parseando HTML de calificaciones...")

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

            print(f"[OK] Parseadas {len(materias)} materias exitosamente")

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
            r'Bienvenido\s*([A-ZÁÉÍÓÚÑ\s]+)',  # Patrón "Bienvenido NOMBRE"
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
                    match = re.search(r'[Bb]ienvenido\s*([A-ZÁÉÍÓÚÑ\s]+)', text)
                    if match:
                        nombre = match.group(1).strip()
                        nombre = re.sub(r'\s+', ' ', nombre)
                        if len(nombre.split()) >= 2:
                            info["nombre"] = nombre
                            break

        # Fallback adicional: buscar en el div.username de la página principal
        if "nombre" not in info:
            username_div = self.soup.find('div', class_='username')
            if username_div:
                highlight = username_div.find(['span', 'strong'])
                candidate = (highlight or username_div).get_text(strip=True)
                candidate = re.sub(r'\s+', ' ', candidate)
                if candidate:
                    # El div incluye "Bienvenido" al inicio; eliminarlo si aparece
                    candidate = re.sub(r'^[Bb]ienvenido\s*', '', candidate)
                    if len(candidate.split()) >= 2:
                        info["nombre"] = candidate.strip()

        # Fallback final: recorrer tablas de perfil (th/td)
        if "nombre" not in info or "matricula" not in info or "periodo" not in info:
            for row in self.soup.find_all('tr'):
                columns = row.find_all(['th', 'td'])
                if len(columns) < 2:
                    continue

                key = columns[0].get_text(strip=True).lower()
                value = columns[1].get_text(strip=True)

                if 'nombre' in key and 'nombre' not in info:
                    cleaned = re.sub(r'\s+', ' ', value)
                    if cleaned and len(cleaned.split()) >= 2:
                        info['nombre'] = cleaned
                elif ('matrícula' in key or 'matricula' in key) and 'matricula' not in info:
                    digits = re.search(r'\d{6,}', value)
                    info['matricula'] = digits.group(0) if digits else value.strip()
                elif 'periodo' in key and 'periodo' not in info:
                    info['periodo'] = value.strip()

                # Si ya obtuvimos todos, terminamos pronto
                if 'nombre' in info and 'matricula' in info and 'periodo' in info:
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

        best_table = None
        best_score = 0

        for table in tables:
            # Buscar headers en la tabla
            headers = table.find_all('th')
            header_texts = [th.get_text(strip=True).lower() for th in headers]
            header_blob = ' '.join(header_texts)

            # Si contiene palabras clave relacionadas con calificaciones
            keywords = ['materia', 'calificación', 'parcial', 'p1', 'p2', 'p3', 'grupo', 'profesor']
            match_count = sum(1 for keyword in keywords if keyword in header_blob)

            # Calcular un puntaje simple para escoger la mejor tabla
            score = match_count
            if 'materia' in header_blob:
                score += 3
            if 'calificación' in header_blob:
                score += 2
            if any(f'p{i}' in header_blob for i in range(1, 6)):
                score += 1

            if score > best_score:
                best_score = score
                best_table = table

        if best_table and best_score >= 3:
            return best_table

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
            print(f"[WARN] Error al parsear fila: {str(e)}")
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
        print(f"[INFO] HTML guardado para debugging en: {filepath}")


def parse_kardex(html: str) -> List[Dict[str, str]]:
    """
    Parsea el kardex académico desde el HTML de la página de calificaciones.
    
    El kardex contiene el historial completo de materias cursadas con:
    número, clave, nombre, cuatrimestre, calificación y tipo de evaluación.
    
    Args:
        html: HTML de la página de calificaciones con kardex
        
    Returns:
        Lista de diccionarios con datos de cada materia del kardex
        
    Ejemplo de retorno:
        [
            {
                'numero': '1',
                'clave': '',
                'materia': 'ÁLGEBRA LINEAL',
                'cuatrimestre': '1',
                'calificacion': '8',
                'tipo_evaluacion': 'CURSO ORDINARIO'
            },
            ...
        ]
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Buscar el div o sección que contiene "Kardex"
    kardex_section = None
    
    # Buscar en los tabs
    for div in soup.find_all('div'):
        title_attr = div.get('title', '')
        if 'kardex' in title_attr.lower():
            kardex_section = div
            break
    
    if not kardex_section:
        print("[WARN] No se encontró la sección de Kardex en el HTML")
        return []
    
    # Encontrar la tabla dentro de la sección kardex
    table = kardex_section.find('table', class_='grid')
    if not table:
        print("[WARN] No se encontró tabla en la sección de Kardex")
        return []
    
    materias = []
    for row in table.find_all('tr', class_=['row0', 'row1']):
        cells = row.find_all('td')
        if len(cells) >= 6:
            materia = {
                'numero': cells[0].text.strip(),
                'clave': cells[1].text.strip(),
                'materia': cells[2].text.strip(),
                'cuatrimestre': cells[3].text.strip(),
                'calificacion': cells[4].text.strip(),
                'tipo_evaluacion': cells[5].text.strip()
            }
            materias.append(materia)
    
    print(f"[OK] Kardex parseado: {len(materias)} materias encontradas")
    return materias


def parse_student_profile(html: str) -> Dict[str, str]:
    """
    Parsea el perfil del estudiante desde el HTML del home.
    
    Extrae todos los datos del perfil: nombre, matrícula, carrera, promedio,
    créditos, nivel de inglés, tutor, etc.
    
    Args:
        html: HTML de la página home
        
    Returns:
        Diccionario con datos del perfil
        
    Ejemplo de retorno:
        {
            'nombre': 'EMILIANO LEDESMA LEDESMA',
            'matricula': '123046244',
            'carrera': 'SISTEMAS',
            'generacion': '20',
            'grupo': 'S204',
            'ultimo_cuatrimestre': '7',
            'promedio_general': '9.07',
            'materias_aprobadas': '45',
            'creditos': '258/360',
            'materias_no_acreditadas': '0',
            'nivel_ingles': '9',
            'estatus': 'ACTIVO',
            'nss': '49160134976',
            'tutor': 'ALVARADO SALAYANDIA CECILIA',
            'email_tutor': 'cecilia.alvarado@upq.edu.mx',
            'foto_url': '/uploads/fotos/alumnos/20/123046244.jpg'
        }
    """
    soup = BeautifulSoup(html, 'html.parser')
    perfil = {}
    
    # Buscar la tabla admintable (estructura principal del perfil)
    table = soup.find('table', class_='admintable')
    if table:
        for row in table.find_all('tr'):
            th = row.find('th')
            td = row.find('td')
            if th and td:
                # Normalizar el nombre del campo
                campo = th.text.strip().replace(':', '').strip()
                valor = td.text.strip()
                
                # Mapear a los nombres esperados
                campo_map = {
                    'Nombre': 'nombre',
                    'Matricula': 'matricula',
                    'Matrícula': 'matricula',
                    'Carrera': 'carrera',
                    'Generación': 'generacion',
                    'Grupo': 'grupo',
                    'Último Cuatrimestre': 'ultimo_cuatrimestre',
                    'Promedio General': 'promedio_general',
                    'Materias Aprobadas': 'materias_aprobadas',
                    'Créditos Aprobados': 'creditos_aprobados',
                    'Materias No Acreditadas': 'materias_no_acreditadas',
                    'Nivel Inglés': 'nivel_ingles',
                    'Estatus Actual': 'estatus',
                    'NSS': 'nss',
                    'Tutores': 'tutor',
                    'Correo Tutor': 'email_tutor',
                    'Servicio Social': 'servicio_social',
                    'Bloque Presencial': 'bloque_presencial'
                }
                
                campo_key = campo_map.get(campo, campo.lower().replace(' ', '_'))
                if valor:  # Solo agregar si tiene valor
                    perfil[campo_key] = valor
    
    # Extraer foto si existe
    foto_img = soup.find('img', src=re.compile(r'/uploads/fotos/alumnos/'))
    if foto_img:
        perfil['foto_url'] = foto_img['src']
    
    # Extraer nombre de usuario del header
    username_div = soup.find('div', class_='username')
    if username_div:
        username_span = username_div.find('span', style=re.compile(r'font-weight:bold'))
        if username_span:
            perfil['nombre_usuario'] = username_span.text.strip()
    
    print(f"[OK] Perfil parseado: {len(perfil)} campos encontrados")
    return perfil


def parse_carga_academica(html: str) -> Dict:
    """
    Parsea la carga académica actual del estudiante.
    
    Extrae las materias del cuatrimestre en curso con información de:
    aula, grupo, profesor, calificaciones parciales y finales.
    
    Args:
        html: HTML de la página de carga académica
        
    Returns:
        Diccionario con periodo y lista de materias
        
    Ejemplo de retorno:
        {
            'periodo': 'CARGA ACADÉMICA: SEPTIEMBRE-DICIEMBRE 2025',
            'materias': [
                {
                    'numero': '1',
                    'clave': '',
                    'materia': 'LIDERAZGO DE EQUIPOS DE ALTO DESEMPEÑO',
                    'aula': 'C104',
                    'grupo': 'S204-7',
                    'profesor': 'RAMIREZ RESENDIZ ADRIANA KARINA',
                    'parciales': {'p1': '9.35', 'p2': '', 'p3': ''},
                    'finales': {'pf1': '', 'pf2': '', 'pf3': ''},
                    'calificacion_final': ''
                },
                ...
            ]
        }
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extraer título del periodo
    titulo_h4 = soup.find('h4', class_='title')
    periodo = titulo_h4.text.strip() if titulo_h4 else "Periodo actual"
    
    # Extraer tabla
    table = soup.find('table', id='tblMaterias')
    if not table:
        return {'periodo': periodo, 'materias': []}
    
    materias = []
    for row in table.find_all('tr', class_=['row0', 'row1']):
        cells = row.find_all('td')
        if len(cells) >= 13:
            materia = {
                'numero': cells[0].text.strip(),
                'clave': cells[1].text.strip(),
                'materia': cells[2].text.strip(),
                'aula': cells[3].text.strip(),
                'grupo': cells[4].text.strip(),
                'profesor': cells[5].text.strip(),
                'parciales': {
                    'p1': cells[6].text.strip(),
                    'p2': cells[7].text.strip(),
                    'p3': cells[8].text.strip(),
                },
                'finales': {
                    'pf1': cells[9].text.strip(),
                    'pf2': cells[10].text.strip(),
                    'pf3': cells[11].text.strip(),
                },
                'calificacion_final': cells[12].text.strip()
            }
            materias.append(materia)
    
    print(f"[OK] Carga académica parseada: {len(materias)} materias encontradas")
    return {
        'periodo': periodo,
        'materias': materias
    }


def parse_historial_academico(html: str) -> List[Dict]:
    """
    Parsea el historial académico completo del estudiante.
    
    Extrae todas las materias cursadas con fecha, ciclo, créditos,
    calificación, tipo de evaluación y estado.
    
    Args:
        html: HTML de la página de historial académico
        
    Returns:
        Lista de diccionarios con datos de cada materia
        
    Ejemplo de retorno:
        [
            {
                'numero': '1',
                'fecha': '15/08/2025',
                'ciclo': 'MAYO - AGOSTO 2025',
                'clave': '',
                'materia': 'ADMINISTRACIÓN DE BASE DE DATOS',
                'creditos': '7',
                'calificacion': '9',
                'tipo_evaluacion': 'CURSO ORDINARIO',
                'tipo_evaluacion_codigo': '1',
                'estado': ''
            },
            ...
        ]
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Buscar la tabla principal del historial
    table = soup.find('table', class_='grid')
    if not table:
        print("[WARN] No se encontró tabla de historial académico")
        return []
    
    historial = []
    for row in table.find_all('tr', class_=['row0', 'row1']):
        cells = row.find_all('td')
        if len(cells) >= 9:
            # Extraer tipo de evaluación del atributo title
            tipo_eval_td = cells[7]
            tipo_eval_titulo = tipo_eval_td.get('title', tipo_eval_td.text.strip())
            tipo_eval_codigo = tipo_eval_td.text.strip()
            
            materia = {
                'numero': cells[0].text.strip(),
                'fecha': cells[1].text.strip(),
                'ciclo': cells[2].text.strip(),
                'clave': cells[3].text.strip(),
                'materia': cells[4].text.strip(),
                'creditos': cells[5].text.strip(),
                'calificacion': cells[6].text.strip(),
                'tipo_evaluacion': tipo_eval_titulo,
                'tipo_evaluacion_codigo': tipo_eval_codigo,
                'estado': cells[8].text.strip()
            }
            historial.append(materia)
    
    print(f"[OK] Historial académico parseado: {len(historial)} registros encontrados")
    return historial


def parse_mapa_curricular(html: str) -> Dict[str, List[Dict]]:
    """
    Parsea el mapa curricular completo de la carrera.
    
    Extrae el plan de estudios completo organizado por ciclos de formación
    y cuatrimestres, mostrando todas las materias con calificaciones,
    tipo de evaluación e intentos.
    
    Args:
        html: HTML de la página de información general del alumno
        
    Returns:
        Diccionario con cuatrimestres como keys y listas de materias como values
        
    Ejemplo de retorno:
        {
            '1er. Cuatrimestre': [
                {
                    'numero': '1',
                    'materia': 'INGLÉS I',
                    'calificacion': '10',
                    'tipo_evaluacion': '11',
                    'intentos': '1',
                    'acreditada': True
                },
                ...
            ],
            '2do. Cuatrimestre': [...],
            ...
        }
    """
    soup = BeautifulSoup(html, 'html.parser')
    mapa = {}
    
    # Encontrar todos los fieldsets (ciclos de formación)
    for fieldset in soup.find_all('fieldset'):
        legend = fieldset.find('legend')
        if not legend:
            continue
            
        ciclo_nombre = legend.text.strip()
        
        # Encontrar todas las tablas de cuatrimestres dentro del ciclo
        for table in fieldset.find_all('table', class_='grid'):
            # Obtener el nombre del cuatrimestre del header
            header = table.find('thead')
            if not header:
                continue
                
            th = header.find('th', attrs={'colspan': True})
            if not th:
                continue
                
            cuatrimestre = th.text.strip()
            
            materias = []
            for row in table.find_all('tr', class_=['row0', 'row1']):
                # Verificar si la materia está acreditada
                acreditada = 'acreditado' in row.get('class', [])
                
                cells = row.find_all('td')
                if len(cells) >= 5:
                    materia = {
                        'numero': cells[0].text.strip(),
                        'materia': cells[1].text.strip(),
                        'calificacion': cells[2].text.strip(),
                        'tipo_evaluacion': cells[3].text.strip(),
                        'intentos': cells[4].text.strip(),
                        'acreditada': acreditada
                    }
                    materias.append(materia)
            
            if materias:
                mapa[cuatrimestre] = materias
    
    print(f"[OK] Mapa curricular parseado: {len(mapa)} cuatrimestres encontrados")
    return mapa


def parse_horario(html: str) -> List[Dict]:
    """
    Parsea el horario semanal de clases.
    
    Extrae el horario completo con día, horas, aula, materia y profesor.
    
    Args:
        html: HTML de la página de horario de materias
        
    Returns:
        Lista de diccionarios con datos de cada clase
        
    Ejemplo de retorno:
        [
            {
                'dia': 'LUNES',
                'hora_inicio': '08:00:00',
                'hora_fin': '10:00:00',
                'aula': 'C104',
                'materia': 'PROGRAMACIÓN WEB',
                'profesor': 'MOYA MOYA JOSE JAVIER'
            },
            ...
        ]
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Buscar la tabla del horario
    table = soup.find('table', class_='grid')
    if not table:
        print("[WARN] No se encontró tabla de horario")
        return []
    
    horario = []
    for row in table.find_all('tr', class_=['row0', 'row1']):
        cells = row.find_all('td')
        if len(cells) >= 6:
            clase = {
                'dia': cells[0].text.strip(),
                'hora_inicio': cells[1].text.strip(),
                'hora_fin': cells[2].text.strip(),
                'aula': cells[3].text.strip(),
                'materia': cells[4].text.strip(),
                'profesor': cells[5].text.strip()
            }
            horario.append(clase)
    
    print(f"[OK] Horario parseado: {len(horario)} clases encontradas")
    return horario


def parse_boleta(html: str) -> Dict[str, Any]:
    """
    Parsea la boleta de calificaciones.
    
    Extrae calificaciones organizadas por cuatrimestre con promedios.
    
    Args:
        html: HTML de la página de boleta de calificaciones
        
    Returns:
        Diccionario con cuatrimestres y sus materias
        
    Ejemplo de retorno:
        {
            'cuatrimestres': [
                {
                    'numero': '7',
                    'nombre': 'SÉPTIMO CUATRIMESTRE',
                    'promedio': '9.14',
                    'creditos': '34',
                    'materias': [
                        {
                            'materia': 'BASE DE DATOS',
                            'calificacion': '8',
                            'creditos': '8'
                        },
                        ...
                    ]
                },
                ...
            ]
        }
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    cuatrimestres = []
    
    # Buscar todas las tablas de cuatrimestres
    for table in soup.find_all('table', class_='grid'):
        # Buscar el header del cuatrimestre
        header = table.find('thead')
        if not header:
            continue
            
        th = header.find('th', attrs={'colspan': True})
        if not th:
            continue
            
        nombre_cuatri = th.text.strip()
        
        # Extraer número de cuatrimestre si está en el nombre
        numero_match = re.search(r'(\d+)', nombre_cuatri)
        numero = numero_match.group(1) if numero_match else '0'
        
        materias = []
        promedio = ''
        creditos = ''
        
        for row in table.find_all('tr', class_=['row0', 'row1']):
            cells = row.find_all('td')
            if len(cells) >= 3:
                # Verificar si es la fila de promedio
                if 'promedio' in cells[0].text.lower():
                    promedio = cells[1].text.strip()
                    creditos = cells[2].text.strip() if len(cells) > 2 else ''
                else:
                    materia = {
                        'materia': cells[0].text.strip(),
                        'calificacion': cells[1].text.strip(),
                        'creditos': cells[2].text.strip() if len(cells) > 2 else ''
                    }
                    materias.append(materia)
        
        if materias:
            cuatrimestres.append({
                'numero': numero,
                'nombre': nombre_cuatri,
                'promedio': promedio,
                'creditos': creditos,
                'materias': materias
            })
    
    print(f"[OK] Boleta parseada: {len(cuatrimestres)} cuatrimestres encontrados")
    return {'cuatrimestres': cuatrimestres}


def parse_pagos(html: str) -> List[Dict]:
    """
    Parsea el historial de pagos.
    
    Extrae todos los pagos realizados con fecha, folio, concepto y monto.
    
    Args:
        html: HTML de la página de pagos
        
    Returns:
        Lista de diccionarios con datos de cada pago
        
    Ejemplo de retorno:
        [
            {
                'fecha': '15/08/2025',
                'folio': 'F123456',
                'concepto': 'COLEGIATURA SEPTIEMBRE',
                'monto': '$2,500.00',
                'forma_pago': 'TRANSFERENCIA'
            },
            ...
        ]
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Buscar la tabla de pagos
    table = soup.find('table', class_='grid')
    if not table:
        print("[WARN] No se encontró tabla de pagos")
        return []
    
    pagos = []
    for row in table.find_all('tr', class_=['row0', 'row1']):
        cells = row.find_all('td')
        if len(cells) >= 5:
            pago = {
                'fecha': cells[0].text.strip(),
                'folio': cells[1].text.strip(),
                'concepto': cells[2].text.strip(),
                'monto': cells[3].text.strip(),
                'forma_pago': cells[4].text.strip()
            }
            pagos.append(pago)
    
    print(f"[OK] Pagos parseados: {len(pagos)} registros encontrados")
    return pagos


def parse_adeudos(html: str) -> List[Dict]:
    """
    Parsea los adeudos pendientes.
    
    Extrae adeudos con concepto, monto y fecha límite.
    
    Args:
        html: HTML de la página de adeudos
        
    Returns:
        Lista de diccionarios con datos de cada adeudo
        
    Ejemplo de retorno:
        [
            {
                'concepto': 'COLEGIATURA OCTUBRE',
                'monto': '$2,500.00',
                'fecha_limite': '31/10/2025',
                'estado': 'PENDIENTE'
            },
            ...
        ]
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Buscar la tabla de adeudos
    table = soup.find('table', class_='grid')
    if not table:
        print("[WARN] No se encontró tabla de adeudos")
        return []
    
    adeudos = []
    for row in table.find_all('tr', class_=['row0', 'row1']):
        cells = row.find_all('td')
        
        # Verificar si es el mensaje de "No se encontraron registros"
        if len(cells) == 1 or 'no se encontraron' in cells[0].text.lower():
            continue
            
        if len(cells) >= 3:
            adeudo = {
                'concepto': cells[0].text.strip(),
                'monto': cells[1].text.strip(),
                'fecha_limite': cells[2].text.strip() if len(cells) > 2 else '',
                'estado': cells[3].text.strip() if len(cells) > 3 else 'PENDIENTE'
            }
            adeudos.append(adeudo)
    
    print(f"[OK] Adeudos parseados: {len(adeudos)} registros encontrados")
    return adeudos


def parse_documentos(html: str) -> List[Dict]:
    """
    Parsea los documentos en proceso.
    
    Extrae documentos solicitados con folio, tipo, fecha y estado.
    
    Args:
        html: HTML de la página de documentos en proceso
        
    Returns:
        Lista de diccionarios con datos de cada documento
        
    Ejemplo de retorno:
        [
            {
                'folio': 'DOC-12345',
                'documento': 'CONSTANCIA DE ESTUDIOS',
                'fecha_solicitud': '01/09/2025',
                'estado': 'EN PROCESO',
                'fecha_entrega': '05/09/2025'
            },
            ...
        ]
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Buscar la tabla de documentos
    table = soup.find('table', class_='grid')
    if not table:
        print("[WARN] No se encontró tabla de documentos")
        return []
    
    documentos = []
    for row in table.find_all('tr', class_=['row0', 'row1']):
        cells = row.find_all('td')
        
        # Verificar si es el mensaje de "No se encontraron registros"
        if len(cells) == 1 or 'no se encontraron' in cells[0].text.lower():
            continue
            
        if len(cells) >= 4:
            documento = {
                'folio': cells[0].text.strip(),
                'documento': cells[1].text.strip(),
                'fecha_solicitud': cells[2].text.strip(),
                'estado': cells[3].text.strip(),
                'fecha_entrega': cells[4].text.strip() if len(cells) > 4 else ''
            }
            documentos.append(documento)
    
    print(f"[OK] Documentos parseados: {len(documentos)} registros encontrados")
    return documentos


def parse_seguimiento_cuatrimestral(html: str) -> List[Dict]:
    """
    Parsea el seguimiento cuatrimestral (calendario académico).
    
    Extrae información de progreso por cuatrimestre con promedios y créditos.
    
    Args:
        html: HTML de la página de seguimiento cuatrimestral
        
    Returns:
        Lista de diccionarios con datos de cada cuatrimestre
        
    Ejemplo de retorno:
        [
            {
                'cuatrimestre': '1',
                'nombre': 'PRIMER CUATRIMESTRE',
                'periodo': 'SEPTIEMBRE - DICIEMBRE 2020',
                'promedio': '9.14',
                'creditos': '48',
                'creditos_acumulados': '48',
                'estado': 'CONCLUIDO'
            },
            ...
        ]
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Buscar la tabla de seguimiento
    table = soup.find('table', class_='grid')
    if not table:
        print("[WARN] No se encontró tabla de seguimiento cuatrimestral")
        return []
    
    seguimiento = []
    for row in table.find_all('tr', class_=['row0', 'row1']):
        cells = row.find_all('td')
        if len(cells) >= 6:
            cuatri = {
                'cuatrimestre': cells[0].text.strip(),
                'nombre': cells[1].text.strip(),
                'periodo': cells[2].text.strip(),
                'promedio': cells[3].text.strip(),
                'creditos': cells[4].text.strip(),
                'creditos_acumulados': cells[5].text.strip(),
                'estado': cells[6].text.strip() if len(cells) > 6 else ''
            }
            seguimiento.append(cuatri)
    
    print(f"[OK] Seguimiento parseado: {len(seguimiento)} cuatrimestres encontrados")
    return seguimiento


def parse_estancias(html: str) -> List[Dict]:
    """
    Parsea las estancias profesionales y estadía del estudiante.
    
    Extrae información completa de estancias I, II y estadía profesional
    desde la sección "Estancias y Estadía" del endpoint de información general.
    
    Args:
        html: HTML de la página de información general (alumno_informacion_general)
        
    Returns:
        Lista de diccionarios con datos de cada estancia/estadía
        
    Ejemplo de retorno:
        [
            {
                'numero': '1',
                'curso': 'Estancia I',
                'empresa': 'UNIVERSIDAD POLITECNICA DE QUERETARO',
                'descripcion': 'Este curso ofrece conocimientos...',
                'periodo': 'ENERO - ABRIL 2025',
                'estatus': 'CONCLUIDO'
            },
            {
                'numero': '2',
                'curso': 'Estancia II',
                'empresa': 'SECRETARIA DE EDUCACION DEL ESTADO DE QUERETARO',
                'descripcion': 'Obtencion de estadistica educativa...',
                'periodo': 'SEPTIEMBRE-DICIEMBRE 2025',
                'estatus': 'AUTORIZADO'
            }
        ]
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Buscar la sección de estancias
    estancias_section = None
    for fieldset in soup.find_all('fieldset'):
        legend = fieldset.find('legend')
        if legend and 'Estancias y Estad' in legend.text:
            estancias_section = fieldset
            break
    
    if not estancias_section:
        print("[WARN] No se encontró sección de estancias")
        return []
    
    # Buscar la tabla dentro de la sección
    table = estancias_section.find('table', class_='grid')
    if not table:
        print("[WARN] No se encontró tabla de estancias")
        return []
    
    estancias = []
    for row in table.find_all('tr', class_=['row0', 'row1']):
        cells = row.find_all('td')
        if len(cells) >= 6:
            estancia = {
                'numero': cells[0].text.strip(),
                'curso': cells[1].text.strip(),
                'empresa': cells[2].text.strip(),
                'descripcion': cells[3].text.strip(),
                'periodo': cells[4].text.strip(),
                'estatus': cells[5].text.strip()
            }
            estancias.append(estancia)
    
    print(f"[OK] Estancias parseadas: {len(estancias)} registros encontrados")
    return estancias


def parse_servicio_social(html: str) -> Dict[str, Any]:
    """
    Parsea el estatus del servicio social del estudiante.
    
    Extrae información del servicio social desde la sección correspondiente
    del endpoint de información general.
    
    Args:
        html: HTML de la página de información general (alumno_informacion_general)
        
    Returns:
        Diccionario con datos del servicio social
        
    Ejemplo de retorno:
        {
            'activo': False,
            'materias_requeridas': '45',
            'materias_faltantes': '0',
            'estatus': 'NO CONCLUIDO',
            'cumple_requisitos': False
        }
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Buscar la sección de servicio social
    servicio_section = None
    for fieldset in soup.find_all('fieldset'):
        legend = fieldset.find('legend')
        if legend and 'Servicio Social' in legend.text:
            servicio_section = fieldset
            break
    
    if not servicio_section:
        print("[WARN] No se encontró sección de servicio social")
        return {}
    
    servicio = {}
    
    # Buscar todas las tablas admintable dentro del fieldset
    tables = servicio_section.find_all('table', class_='admintable')
    
    if tables:
        # Cada tabla tiene una fila con th y td
        for table in tables:
            row = table.find('tr')
            if row:
                th = row.find('th')
                td = row.find('td')
                if th and td:
                    key = th.text.strip().rstrip(':')
                    value = td.text.strip()
                    
                    # Orden importa: verificar primero los más específicos
                    if 'Estatus Servicio Social' in key:
                        servicio['estatus'] = value
                    elif 'Materias Requeridas' in key:
                        servicio['materias_requeridas'] = value
                    elif 'Materias Faltantes' in key:
                        servicio['materias_faltantes'] = value
                    elif 'Servicio Social' in key:
                        servicio['activo'] = value.upper() == 'SI'
    else:
        # Fallback: buscar tabla grid si no hay admintable
        table = servicio_section.find('table', class_='grid')
        if table:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    key = cells[0].text.strip().rstrip(':')
                    value = cells[1].text.strip()
                    
                    # Orden importa: verificar primero los más específicos
                    if 'Estatus Servicio Social' in key:
                        servicio['estatus'] = value
                    elif 'Materias Requeridas' in key:
                        servicio['materias_requeridas'] = value
                    elif 'Materias Faltantes' in key:
                        servicio['materias_faltantes'] = value
                    elif 'Servicio Social' in key:
                        servicio['activo'] = value.upper() == 'SI'
    
    # Determinar si cumple requisitos
    if 'materias_faltantes' in servicio:
        try:
            servicio['cumple_requisitos'] = int(servicio['materias_faltantes']) == 0
        except ValueError:
            servicio['cumple_requisitos'] = False
    else:
        servicio['cumple_requisitos'] = False
    
    print(f"[OK] Servicio social parseado: {len(servicio)} campos encontrados")
    return servicio


