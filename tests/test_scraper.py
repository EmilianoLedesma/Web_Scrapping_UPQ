"""
Tests básicos para el sistema de scraping UPQ.
Ejecutar con: pytest tests/
"""

import pytest
from scraper.parser import UPQGradesParser, ParserError


# HTML de ejemplo para testing (basado en la estructura real)
SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<body>
    <div>
        <p>Alumno: EMILIANO LEDESMA</p>
        <p>Matrícula: 12304244</p>
        <p>Periodo: SEPTIEMBRE-DICIEMBRE 2025</p>
    </div>

    <table>
        <thead>
            <tr>
                <th>Clave</th>
                <th>Materia</th>
                <th>Aula</th>
                <th>Grupo</th>
                <th>Profesor</th>
                <th>P1</th>
                <th>P2</th>
                <th>P3</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>C104</td>
                <td>LIDERAZGO DE EQUIPOS DE ALTO DESEMPEÑO</td>
                <td>A101</td>
                <td>S204-7</td>
                <td>RAMIREZ RESENDIZ ADRIANA KARIMA</td>
                <td>9.35</td>
                <td>9.20</td>
                <td>P3</td>
            </tr>
            <tr>
                <td>C105</td>
                <td>PROGRAMACIÓN WEB</td>
                <td>B202</td>
                <td>S204-8</td>
                <td>GARCIA LOPEZ JUAN CARLOS</td>
                <td>8.5</td>
                <td>P2</td>
                <td>P3</td>
            </tr>
        </tbody>
    </table>
</body>
</html>
"""


class TestUPQGradesParser:
    """Tests para el parser de calificaciones."""

    def test_parse_student_info(self):
        """Test de extracción de información del alumno."""
        parser = UPQGradesParser(SAMPLE_HTML)
        info = parser._extract_student_info()

        assert info.get("nombre") == "EMILIANO LEDESMA"
        assert info.get("matricula") == "12304244"
        assert "SEPTIEMBRE-DICIEMBRE 2025" in info.get("periodo", "")

    def test_find_grades_table(self):
        """Test de detección de la tabla de calificaciones."""
        parser = UPQGradesParser(SAMPLE_HTML)
        table = parser._find_grades_table()

        assert table is not None
        assert len(table.find_all('tr')) > 0

    def test_parse_grades_complete(self):
        """Test de parseo completo de calificaciones."""
        parser = UPQGradesParser(SAMPLE_HTML)
        result = parser.parse_grades()

        # Verificar estructura del resultado
        assert "alumno" in result
        assert "matricula" in result
        assert "periodo" in result
        assert "materias" in result

        # Verificar datos del alumno
        assert result["alumno"] == "EMILIANO LEDESMA"
        assert result["matricula"] == "12304244"

        # Verificar materias
        materias = result["materias"]
        assert len(materias) == 2

        # Verificar primera materia
        materia1 = materias[0]
        assert materia1["nombre"] == "LIDERAZGO DE EQUIPOS DE ALTO DESEMPEÑO"
        assert materia1["clave"] == "C104"
        assert materia1["grupo"] == "S204-7"
        assert materia1["profesor"] == "RAMIREZ RESENDIZ ADRIANA KARIMA"

        # Verificar calificaciones de la primera materia
        calif1 = materia1["calificaciones"]
        assert calif1.get("P1") == 9.35
        assert calif1.get("P2") == 9.20
        assert calif1.get("P3") is None  # "P3" indica que no hay calificación

    def test_column_mapping(self):
        """Test de mapeo flexible de columnas."""
        parser = UPQGradesParser(SAMPLE_HTML)

        # Headers en diferentes formatos
        headers_variations = [
            ["Materia", "P1", "P2", "P3"],
            ["ASIGNATURA", "Primer Parcial", "Segundo Parcial", "Tercer Parcial"],
            ["Curso", "Calificación P1", "Calificación P2", "Calificación P3"]
        ]

        for headers in headers_variations:
            column_map = parser._map_columns(headers)

            # Debe detectar la columna de materia
            assert "materia" in column_map

            # Debe detectar parciales
            assert "P1" in column_map or any("p1" in h.lower() for h in headers)

    def test_parcial_number_extraction(self):
        """Test de extracción de número de parcial."""
        parser = UPQGradesParser("")

        assert parser._extract_parcial_number("P1") == 1
        assert parser._extract_parcial_number("p2") == 2
        assert parser._extract_parcial_number("Primer Parcial") == 1
        assert parser._extract_parcial_number("segundo parcial") == 2
        assert parser._extract_parcial_number("Tercer Parcial") == 3

    def test_empty_html(self):
        """Test con HTML vacío."""
        parser = UPQGradesParser("<html><body></body></html>")

        with pytest.raises(ParserError):
            parser.parse_grades()

    def test_malformed_html(self):
        """Test con HTML malformado."""
        parser = UPQGradesParser("<html><table><tr><td>test")

        # El parser debe manejar HTML malformado sin crashear
        try:
            result = parser.parse_grades()
            # Si no hay error, debe retornar estructura válida
            assert "materias" in result
        except ParserError:
            # Es aceptable que lance ParserError con HTML muy malformado
            pass

    def test_missing_student_info(self):
        """Test cuando falta información del alumno."""
        html_without_info = """
        <html>
        <body>
            <table>
                <tr>
                    <th>Materia</th>
                    <th>P1</th>
                </tr>
                <tr>
                    <td>TEST MATERIA</td>
                    <td>10</td>
                </tr>
            </table>
        </body>
        </html>
        """

        parser = UPQGradesParser(html_without_info)
        result = parser.parse_grades()

        # Debe funcionar aunque falte info del alumno
        assert "materias" in result
        # Los valores faltantes deben ser "No disponible"
        assert result.get("alumno") == "No disponible"


class TestGradesDataStructure:
    """Tests para validar la estructura de datos de calificaciones."""

    def test_grades_structure(self):
        """Test de la estructura de datos esperada."""
        parser = UPQGradesParser(SAMPLE_HTML)
        result = parser.parse_grades()

        # Verificar que tiene todos los campos requeridos
        required_fields = ["alumno", "matricula", "periodo", "fecha_consulta", "materias"]
        for field in required_fields:
            assert field in result, f"Falta el campo requerido: {field}"

        # Verificar estructura de materias
        for materia in result["materias"]:
            assert "nombre" in materia
            assert "calificaciones" in materia
            assert isinstance(materia["calificaciones"], dict)


class TestParserRobustness:
    """Tests de robustez del parser ante variaciones."""

    def test_case_insensitive_headers(self):
        """Test que el parser funciona con headers en diferentes casos."""
        html = """
        <table>
            <tr>
                <th>MATERIA</th>
                <th>p1</th>
                <th>P2</th>
            </tr>
            <tr>
                <td>Test Subject</td>
                <td>9.5</td>
                <td>8.0</td>
            </tr>
        </table>
        """

        parser = UPQGradesParser(html)
        result = parser.parse_grades()

        assert len(result["materias"]) > 0
        assert result["materias"][0]["nombre"] == "Test Subject"

    def test_extra_whitespace(self):
        """Test que el parser maneja whitespace extra."""
        html = """
        <table>
            <tr>
                <th>  Materia  </th>
                <th>  P1  </th>
            </tr>
            <tr>
                <td>  Test Subject  </td>
                <td>  9.5  </td>
            </tr>
        </table>
        """

        parser = UPQGradesParser(html)
        result = parser.parse_grades()

        # El texto debe estar limpio (sin whitespace extra)
        materia = result["materias"][0]
        assert materia["nombre"] == "Test Subject"
        assert materia["calificaciones"].get("P1") == 9.5

    def test_different_table_structures(self):
        """Test con diferentes estructuras de tabla."""
        # Tabla sin <thead>
        html = """
        <table>
            <tr>
                <td>Materia</td>
                <td>P1</td>
            </tr>
            <tr>
                <td>Test</td>
                <td>10</td>
            </tr>
        </table>
        """

        parser = UPQGradesParser(html)
        result = parser.parse_grades()

        # Debe parsear incluso sin <thead>
        assert "materias" in result


# Fixture para testing con datos reales (opcional)
@pytest.fixture
def sample_grades_data():
    """Fixture con datos de ejemplo."""
    return {
        "alumno": "EMILIANO LEDESMA",
        "matricula": "12304244",
        "periodo": "SEPTIEMBRE-DICIEMBRE 2025",
        "materias": [
            {
                "nombre": "LIDERAZGO",
                "clave": "C104",
                "calificaciones": {
                    "P1": 9.35,
                    "P2": 9.20,
                    "P3": None
                }
            }
        ]
    }


def test_sample_data_structure(sample_grades_data):
    """Test usando fixture de datos de ejemplo."""
    assert "alumno" in sample_grades_data
    assert len(sample_grades_data["materias"]) == 1
    assert sample_grades_data["materias"][0]["calificaciones"]["P1"] == 9.35


if __name__ == "__main__":
    # Permite ejecutar tests directamente
    pytest.main([__file__, "-v"])
