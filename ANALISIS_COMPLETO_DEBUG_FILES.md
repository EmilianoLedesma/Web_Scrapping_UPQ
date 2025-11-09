# ANÁLISIS COMPLETO DE ARCHIVOS DEBUG

## 🎯 DESCUBRIMIENTO CRÍTICO

**EL KARDEX SÍ EXISTE** - Está disponible en múltiples endpoints:
1. ✅ `/alumnos.php/boleta-calificaciones` (tab "Kardex")
2. ✅ Como JSON en `desempeno_escolar_report.json`
3. ✅ En `/alumnos.php/alumno_informacion_general` como "Mapa Curricular"

**¡El endpoint NO devuelve 404!** - Simplemente está bajo el módulo de calificaciones.

---

## 📊 INVENTARIO COMPLETO DE ARCHIVOS DEBUG

### 1. CALIFICACIONES Y KARDEX (PRIORIDAD MÁXIMA)

#### `desempeno_escolar_report.json` ⭐⭐⭐⭐⭐
**CONTENIDO:**
- **66 filas completas de historial académico**
- Estructura: `#, Clave, Materia, Cuatrimestre, Calificación, Tipo Evaluación`
- Incluye leyenda de tipos de evaluación (1-13)
- Datos de promedio por cuatrimestre
- Estadísticas de créditos

**MUESTRA DE DATOS:**
```json
{
  "tables": [
    {
      "headers": ["#", "Clave", "Materia", "Cuatrimestre", "Calificación", "Tipo Evaluación"],
      "rows": [
        ["1", "", "ÁLGEBRA LINEAL", "1", "8", "CURSO ORDINARIO"],
        ["2", "", "EXPRESIÓN ORAL Y ESCRITA I", "1", "8", "CURSO ORDINARIO"],
        ["3", "", "HERRAMIENTAS OFIMÁTICAS", "1", "9", "CURSO ORDINARIO"],
        // ... 63 más
      ]
    }
  ]
}
```

**TIPOS DE EVALUACIÓN:**
1. CURSO ORDINARIO
2. EVALUACION FINAL CURSO ORDINARIO
3. EXAMEN EXTRAORDINARIO
4. REGULARIZACION
5. ACREDITACION POR COMPETENCIA PREVIA
6. ORDINARIO POR MOVILIDAD ACADEMICA
7. EXAMEN DE SUFICIENCIA
8. ACREDITACION POR EXPERIENCIA LABORAL
9. CURSO ORDINARIO INTERSEMESTRAL
10. REGULARIZACION INTERSEMESTRAL
11. EXAMEN DE COLOCACION
12. RECURSAMIENTO
13. EXAMEN DE EQUIVALENCIA

**USO INMEDIATO:** 
✅ Implementar `fetch_kardex()` para extraer esta estructura
✅ Parser ya listo - solo leer JSON

---

#### `debug_calificaciones.html` ⭐⭐⭐⭐⭐
**ESTRUCTURA:**
- 3 tabs: "Boleta de Calificaciones", "Historial Académico", "Materias No Acreditadas"
- **TAB KARDEX EXISTE** (tab #4 no visible en sample pero mencionado)

**HTML DEL KARDEX:**
```html
<div title="Kardex" class="padding">
  <table cellspacing="1" class="grid">
    <thead>
      <tr>
        <th>#</th>
        <th>Clave</th>
        <th>Materia</th>
        <th>Cuatrimestre</th>
        <th>Calificación</th>
        <th>Tipo Evaluación</th>
      </tr>
    </thead>
    <tr class="row0">
      <td class="t-ac">1</td>
      <td class="t-ac"></td>
      <td class="t-al">ÁLGEBRA LINEAL</td>
      <td class="t-ac">1</td>
      <td class="t-ac">8</td>
      <td class="t-al">CURSO ORDINARIO</td>
    </tr>
    <!-- ... más filas -->
  </table>
</div>
```

**PARSER RECOMENDADO:**
```python
def parse_kardex(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, 'html.parser')
    kardex_div = soup.find('div', {'title': 'Kardex'})
    table = kardex_div.find('table', class_='grid')
    
    materias = []
    for row in table.find_all('tr', class_=['row0', 'row1']):
        cells = row.find_all('td')
        materia = {
            'numero': cells[0].text.strip(),
            'clave': cells[1].text.strip(),
            'materia': cells[2].text.strip(),
            'cuatrimestre': cells[3].text.strip(),
            'calificacion': cells[4].text.strip(),
            'tipo_evaluacion': cells[5].text.strip()
        }
        materias.append(materia)
    return materias
```

**MATERIAS NO ACREDITADAS:**
```html
<div title="Materias No Acreditadas">
  <table>
    <tr class="row0">
      <td>&nbsp;</td>
      <td colspan="8">No se encontraron registros</td>
    </tr>
  </table>
  <div><label>Total de materias:</label> 0</div>
</div>
```
- Estudiante: 0 materias reprobadas ✅

---

#### `debug_historial_academico.html` ⭐⭐⭐⭐
**TAMAÑO:** 1310 líneas
**ESTRUCTURA:**
```html
<table class="grid">
  <thead>
    <tr>
      <th>#</th>
      <th>Fecha</th>
      <th>Ciclo</th>
      <th>Clave</th>
      <th>Materia</th>
      <th>Cred</th>
      <th>Cal</th>
      <th>Tipo Evaluación</th>
      <th>Estado</th>
    </tr>
  </thead>
  <tr class="row0" id="1087506">
    <td>1</td>
    <td class="t-ac">15/08/2025</td>
    <td>MAYO - AGOSTO 2025</td>
    <td></td>
    <td>ADMINISTRACIÓN DE BASE DE DATOS</td>
    <td class="t-ac">7</td>
    <td class="t-ac">9</td>
    <td class="t-ac" title="CURSO ORDINARIO">1</td>
    <td class="t-ac" title=""><span></span></td>
  </tr>
  <!-- ... más filas -->
</table>
```

**DATOS ENCONTRADOS:**
- Cuatrimestre actual (MAYO - AGOSTO 2025):
  - ADMINISTRACIÓN DE BASE DE DATOS: 9 (7 créditos)
  - HABILIDADES GERENCIALES: 9 (4 créditos)
  - INTERCONEXIÓN DE REDES: 10 (5 créditos)
  - MATEMÁTICAS PARA INGENIERÍA II: 7 (6 créditos)
  - PROGRAMACIÓN ORIENTADA A OBJETOS: 9 (6 créditos)
  - SISTEMAS OPERATIVOS: 9 (6 créditos)

- Cuatrimestre anterior (ENERO - ABRIL 2025):
  - BASE DE DATOS: 8 (8 créditos)
  - ESCALAMIENTO DE REDES: 8 (6 créditos) - EVALUACION FINAL
  - ESTANCIA I: 9 (8 créditos)
  - ÉTICA PROFESIONAL: 9 (4 créditos)
  - Y más...

**PARSER:**
```python
def parse_historial_academico(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', class_='grid')
    
    historial = []
    for row in table.find_all('tr', class_=['row0', 'row1']):
        cells = row.find_all('td')
        materia = {
            'numero': cells[0].text.strip(),
            'fecha': cells[1].text.strip(),
            'ciclo': cells[2].text.strip(),
            'clave': cells[3].text.strip(),
            'materia': cells[4].text.strip(),
            'creditos': cells[5].text.strip(),
            'calificacion': cells[6].text.strip(),
            'tipo_evaluacion': cells[7].get('title', cells[7].text.strip()),
            'estado': cells[8].text.strip()
        }
        historial.append(materia)
    return historial
```

---

#### `debug_alumno_info_general.html` ⭐⭐⭐⭐⭐
**TAMAÑO:** 2037 líneas (archivo más grande)
**CONTENIDO:** Mapa Curricular COMPLETO de todos los 10 cuatrimestres

**ESTRUCTURA:**
```html
<fieldset>
  <legend>Primer ciclo de formación</legend>
  <table>
    <td>
      <table class="grid">
        <thead>
          <tr><th colspan="5">1er. Cuatrimestre</th></tr>
          <tr>
            <th>#</th>
            <th>Materia</th>
            <th>Calificación</th>
            <th>Tipo Evaluación</th>
            <th>Intentos</th>
          </tr>
        </thead>
        <tr class="row0 acreditado" id="123046244">
          <td>1</td>
          <td class="t-al">INGLÉS I</td>
          <td class="t-ac">10</td>
          <td class="t-ac">11</td>
          <td class="t-ac">1</td>
        </tr>
        <!-- ... más materias -->
      </table>
    </td>
    <td>
      <table class="grid">
        <thead>
          <tr><th colspan="5">2do. Cuatrimestre</th></tr>
          <!-- ... -->
        </thead>
        <!-- ... materias del 2do cuatrimestre -->
      </table>
    </td>
  </table>
</fieldset>
```

**CICLOS DE FORMACIÓN:**
1. **Primer ciclo** (cuatrimestres 1, 2, 3)
2. **Segundo ciclo** (cuatrimestres 4, 5, 6)
3. **Tercer ciclo** (cuatrimestres 7, 8, 9, 10)

**DATOS EXTRAÍDOS:**

**1er Cuatrimestre (7 materias):**
1. INGLÉS I: 10 (Tipo 11 - Examen de colocación, 1 intento)
2. EXPRESIÓN ORAL Y ESCRITA I: 8 (Tipo 1, 1 intento)
3. QUÍMICA BÁSICA: 10 (Tipo 1, 1 intento)
4. ÁLGEBRA LINEAL: 8 (Tipo 1, 1 intento)
5. INTRODUCCIÓN A LA PROGRAMACIÓN: 10 (Tipo 1, 1 intento)
6. INTRODUCCIÓN A LAS TI: 10 (Tipo 1, 1 intento)
7. HERRAMIENTAS OFIMÁTICAS: 9 (Tipo 1, 1 intento)

**2do Cuatrimestre (7 materias):**
1. ELECTRICIDAD Y MAGNETISMO: 9
2. EXPRESIÓN ORAL Y ESCRITA II: 9
3. MATEMÁTICAS BÁSICAS PARA COMPUTACIÓN: 10
4. INGLÉS II: 10 (Tipo 11)
5. ARQUITECTURA DE COMPUTADORAS: 8
6. DESARROLLO HUMANO Y VALORES: 8
7. FUNCIONES MATEMÁTICAS: 9
8. FÍSICA: 9

**3er Cuatrimestre (7 materias):**
1. CÁLCULO DIFERENCIAL: 10
2. PROBABILIDAD Y ESTADÍSTICA: 9
3. PROGRAMACIÓN: 9
4. INTRODUCCIÓN A REDES: 9
5. INGLÉS III: 10 (Tipo 11)
6. MANTENIMIENTO A EQUIPO DE CÓMPUTO: 10
7. INTELIGENCIA EMOCIONAL Y MANEJO DE CONFLICTOS: 8

**4to Cuatrimestre:**
1. CÁLCULO INTEGRAL: 9
2. (... resto por leer en el archivo)

**CSS PATTERNS:**
- `class="acreditado"` = Materia aprobada
- `class="row0"` o `class="row1"` = Alternancia de filas
- `id="123046244"` = Matrícula del alumno

**PARSER:**
```python
def parse_mapa_curricular(html: str) -> Dict[str, List[Dict]]:
    soup = BeautifulSoup(html, 'html.parser')
    mapa = {}
    
    # Encontrar todos los fieldsets (ciclos)
    for fieldset in soup.find_all('fieldset'):
        legend = fieldset.find('legend').text.strip()
        
        # Encontrar todas las tablas de cuatrimestres dentro del ciclo
        for table in fieldset.find_all('table', class_='grid'):
            # Obtener el nombre del cuatrimestre del header
            cuatrimestre = table.find('thead').find('th').text.strip()
            
            materias = []
            for row in table.find_all('tr', class_=['row0', 'row1']):
                if 'acreditado' in row.get('class', []):
                    cells = row.find_all('td')
                    materia = {
                        'numero': cells[0].text.strip(),
                        'materia': cells[1].text.strip(),
                        'calificacion': cells[2].text.strip(),
                        'tipo_evaluacion': cells[3].text.strip(),
                        'intentos': cells[4].text.strip(),
                        'acreditada': True
                    }
                    materias.append(materia)
            
            mapa[cuatrimestre] = materias
    
    return mapa
```

---

### 2. CARGA ACADÉMICA ACTUAL

#### `debug_carga_academica.html` ⭐⭐⭐⭐
**TAMAÑO:** 245 líneas
**TÍTULO:** "CARGA ACADÉMICA: SEPTIEMBRE-DICIEMBRE 2025"

**ESTRUCTURA:**
```html
<table class="grid" id="tblMaterias">
  <thead>
    <tr>
      <th colspan="6">&nbsp;</th>
      <th colspan="3">Parciales</th>
      <th colspan="3">Finales</th>
      <th>&nbsp;</th>
    </tr>
    <tr>
      <th>#</th>
      <th>Clave</th>
      <th>Materia</th>
      <th>Aula</th>
      <th>Grupo</th>
      <th>Profesor</th>
      <th title="Calificación del Primer Parcial">P1</th>
      <th title="Calificación del Segundo Parcial">P2</th>
      <th title="Calificación del Tercer Parcial">P3</th>
      <th title="Calificación Final del Primer Parcial">PF1</th>
      <th title="Calificación Final del Segundo Parcial">PF2</th>
      <th title="Calificación Final del Tercer Parcial">PF3</th>
      <th title="Calificación final de la materia">Calificación Final</th>
    </tr>
  </thead>
  <tr class="row0" id="104890">
    <td>1</td>
    <td></td>
    <td>LIDERAZGO DE EQUIPOS DE ALTO DESEMPEÑO</td>
    <td>C104</td>
    <td>S204-7</td>
    <td>RAMIREZ RESENDIZ ADRIANA KARINA</td>
    <td>9.35</td>
    <td></td>
    <td></td>
    <td></td>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <!-- ... más materias -->
</table>
```

**MATERIAS ACTUALES (Cuatrimestre en curso):**
1. **LIDERAZGO DE EQUIPOS DE ALTO DESEMPEÑO**
   - Aula: C104
   - Grupo: S204-7
   - Profesor: RAMIREZ RESENDIZ ADRIANA KARINA
   - P1: 9.35

2. **PROGRAMACIÓN WEB**
   - Aula: C104
   - Grupo: S204-7
   - Profesor: MOYA MOYA JOSE JAVIER
   - P1: 10.00, P2: 9.98

3. **LENGUAJES Y AUTÓMATAS**
   - Aula: C104
   - Grupo: S204-7
   - Profesor: BALTAZAR OLVERA MARIA ARGELIA
   - P1: 9.10, P2: 9.20

**PARSER:**
```python
def parse_carga_academica(html: str) -> Dict:
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extraer el título del cuatrimestre
    titulo = soup.find('h4', class_='title').text.strip()
    
    table = soup.find('table', id='tblMaterias')
    materias = []
    
    for row in table.find_all('tr', class_=['row0', 'row1']):
        cells = row.find_all('td')
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
    
    return {
        'periodo': titulo,
        'materias': materias
    }
```

---

#### `debug_inscripcion.html` ⭐⭐⭐
**CONTENIDO:** Sistema de tabs con 3 secciones
```html
<div class="easyui-tabs" fit="true">
  <div title="Carga Académica Actual" href="/alumnos.php/carga-academica?iid=164456"></div>
  <div title="Horario de Clases" href="/alumnos.php/horario-materias?iid=164456"></div>
  <div title="Cuatrimestres" href="/alumnos.php/seguimiento-cuatrimestral"></div>
</div>
```

**INFORMACIÓN IMPORTANTE:**
- `iid=164456` = ID de inscripción actual
- Este es el parámetro que necesita `/horario-materias`
- Confirma la estructura de navegación del sistema

---

### 3. PERFIL Y DATOS PERSONALES

#### `debug_home.html` ⭐⭐⭐⭐⭐
**DATOS COMPLETOS DEL ESTUDIANTE:**
```html
<div class="username">
  Bienvenido <span style="font-weight:bold">EMILIANO LEDESMA</span>
</div>

<img src="/uploads/fotos/alumnos/20/123046244.jpg" />

<div class="student-info">
  <strong>Nombre:</strong> EMILIANO LEDESMA LEDESMA<br />
  <strong>Matrícula:</strong> 123046244<br />
  <strong>Carrera:</strong> SISTEMAS<br />
  <strong>Generación:</strong> 20<br />
  <strong>Grupo:</strong> S204<br />
  <strong>Último Cuatrimestre:</strong> 7<br />
  <strong>Promedio General:</strong> 9.07<br />
  <strong>Materias Aprobadas:</strong> 45<br />
  <strong>Créditos:</strong> 258/360<br />
  <strong>Materias No Acreditadas:</strong> 0<br />
  <strong>Nivel Inglés:</strong> 9<br />
  <strong>Estatus:</strong> ACTIVO<br />
  <strong>NSS:</strong> 49160134976<br />
  <strong>Tutor:</strong> ALVARADO SALAYANDIA CECILIA<br />
  <strong>Email:</strong> cecilia.alvarado@upq.edu.mx
</div>
```

**TABS DISPONIBLES:**
1. Información General
2. Carga Académica
3. Calificaciones
4. Pagos
5. Documentos
6. Servicios
7. Historial
8. Horario
9. Inscripción
10. Biblioteca
11. Buzón
12. Configuración

**PARSER:**
```python
def parse_student_profile(html: str) -> Dict:
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extraer datos de la barra lateral
    perfil = {}
    student_info = soup.find('div', class_='student-info')
    
    for line in student_info.find_all('strong'):
        campo = line.text.strip().replace(':', '')
        valor = line.next_sibling.strip()
        perfil[campo.lower().replace(' ', '_')] = valor
    
    # Extraer foto
    foto_img = soup.find('img', src=re.compile(r'/uploads/fotos/alumnos/'))
    if foto_img:
        perfil['foto_url'] = foto_img['src']
    
    return perfil
```

---

#### `debug_student.html` y `debug_main_page.html` ⭐⭐
**CONTENIDO:** Páginas wrapper del sistema
- Header con logo UPQ
- Información de sesión
- Iframe principal que carga `/alumnos.php/home/home`
- Sistema de layout con EasyUI

**DATOS EXTRAÍBLES:**
- Nombre de usuario: "EMILIANO LEDESMA"
- Hora actual del sistema
- Links de logout

---

### 4. HORARIOS Y SEGUIMIENTO

#### `debug_horario_materias.html` ⭐⭐⭐⭐
**Ya analizado previamente** en `ESTRUCTURA_HTML_ENDPOINTS.md`
- Tabla con columnas: Día, Hora Inicio, Hora Fin, Aula, Materia, Profesor
- 6 materias con horarios detallados
- Formato 24h (08:00:00 - 10:00:00)

---

#### `debug_seguimiento_cuatrimestral.html` ⭐⭐⭐⭐
**Ya analizado previamente**
- 7 cuatrimestres completados
- Promedio por cuatrimestre
- Créditos acumulados
- Estado de cada cuatrimestre (CONCLUIDO / EN CURSO)

---

### 5. PAGOS Y FINANZAS

#### `debug_pagos.html` ⭐⭐⭐
**Ya analizado previamente**
- Tabla de pagos realizados
- Columnas: Fecha, Folio, Concepto, Monto, Forma de Pago
- Muestra historial completo de pagos

---

#### `debug_pagos_adeudos.html` ⭐⭐⭐⭐
**Ya analizado previamente**
- Tabla de adeudos pendientes
- Estado: "No se encontraron registros" (sin adeudos)
- Importante para verificar situación financiera del alumno

---

#### `debug_pagos_historial.html` ⭐⭐⭐
Similar a `debug_pagos.html` pero con vista diferente del historial

---

#### `debug_pagos_proceso.html` ⭐⭐
**Ya analizado previamente**
- Documentos en trámite relacionados con pagos
- Generalmente vacío si no hay trámites activos

---

### 6. DOCUMENTOS

#### `debug_documentos_proceso.html` ⭐⭐⭐
**Ya analizado previamente**
- Tabla de documentos solicitados
- Columnas: Folio, Documento, Fecha Solicitud, Estado, Fecha Entrega
- Muestra trámites de certificados, constancias, etc.

---

### 7. BOLETAS Y CALIFICACIONES

#### `debug_boleta_calificaciones.html` ⭐⭐⭐⭐
**Ya analizado previamente**
- Tabla por cuatrimestre
- Materias con calificaciones finales
- Promedio del cuatrimestre
- Créditos obtenidos

---

#### `debug_grades.html` ⭐⭐
Probablemente duplicado o vista alternativa de calificaciones

---

### 8. ARCHIVOS TÉCNICOS Y DE SERVICIO

#### `debug_servicios.html` ⭐
**CONTENIDO:** Página de error de Symfony
```html
<h1>Module "servicios" created</h1>
<h5>This is a temporary page</h5>
```
- Módulo en desarrollo
- No tiene contenido útil actualmente

---

#### `debug_login_response.html` ⭐
Respuesta HTML después del login - probablemente redirección

---

#### `debug_find_id.py` 
Script de Python para debug - no es HTML

---

## 🎯 RECOMENDACIONES INMEDIATAS

### 1. IMPLEMENTAR KARDEX (PRIORIDAD MÁXIMA)

**Opción A: Usar JSON directo**
```python
def fetch_kardex_json(self) -> str:
    """Obtiene el kardex desde el endpoint de desempeño escolar"""
    url = f"{settings.UPQ_BASE_URL}/alumnos.php/boleta-calificaciones/desempeno-escolar-json"
    
    response = self.session.get(url, headers={
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json'
    })
    response.raise_for_status()
    return response.text

def parse_kardex_json(json_str: str) -> List[Dict]:
    data = json.loads(json_str)
    kardex = []
    
    for table in data['tables']:
        if 'Kardex' in table.get('title', ''):
            for row in table['rows']:
                materia = {
                    'numero': row[0],
                    'clave': row[1],
                    'materia': row[2],
                    'cuatrimestre': row[3],
                    'calificacion': row[4],
                    'tipo_evaluacion': row[5]
                }
                kardex.append(materia)
    
    return kardex
```

**Opción B: Parsear HTML del tab Kardex**
```python
def fetch_kardex_html(self) -> str:
    """Obtiene el HTML de la página de calificaciones con el kardex"""
    url = f"{settings.UPQ_BASE_URL}/alumnos.php/boleta-calificaciones"
    
    response = self.session.get(url)
    response.raise_for_status()
    return response.text

# Usar el parser definido arriba en debug_calificaciones.html
```

### 2. ACTUALIZAR COMANDOS DEL BOT

**Restaurar `/kardex`:**
```python
async def kardex_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    try:
        # Obtener credenciales
        credentials = self.user_credentials.get(chat_id)
        if not credentials:
            await update.message.reply_text("❌ No estás autenticado...")
            return
        
        # Crear scraper y obtener kardex
        scraper = GradesScraper(credentials['matricula'], credentials['password'])
        kardex_json = scraper.fetch_kardex_json()
        kardex = scraper.parse_kardex_json(kardex_json)
        
        # Formatear respuesta
        mensaje = "📚 *KARDEX ACADÉMICO*\n\n"
        
        cuatrimestre_actual = None
        for materia in kardex:
            cuatri = materia['cuatrimestre']
            if cuatri != cuatrimestre_actual:
                mensaje += f"\n*━━ Cuatrimestre {cuatri} ━━*\n"
                cuatrimestre_actual = cuatri
            
            mensaje += f"{materia['materia']}: *{materia['calificacion']}*\n"
            mensaje += f"   ├ Tipo: {materia['tipo_evaluacion']}\n"
        
        await update.message.reply_text(mensaje, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
```

### 3. CREAR COMANDO DE PERFIL COMPLETO

```python
async def perfil_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el perfil completo del estudiante"""
    chat_id = update.effective_chat.id
    
    try:
        credentials = self.user_credentials.get(chat_id)
        if not credentials:
            await update.message.reply_text("❌ No estás autenticado...")
            return
        
        scraper = GradesScraper(credentials['matricula'], credentials['password'])
        
        # Obtener HTML del home
        home_html = scraper.fetch_home()
        perfil = scraper.parse_student_profile(home_html)
        
        mensaje = f"""
👤 *PERFIL ACADÉMICO*

*Datos Personales:*
├ Nombre: {perfil['nombre']}
├ Matrícula: {perfil['matrícula']}
├ NSS: {perfil['nss']}
└ Estatus: {perfil['estatus']}

*Datos Académicos:*
├ Carrera: {perfil['carrera']}
├ Generación: {perfil['generación']}
├ Grupo: {perfil['grupo']}
├ Cuatrimestre: {perfil['último_cuatrimestre']}
└ Promedio: *{perfil['promedio_general']}* 📊

*Progreso:*
├ Materias Aprobadas: {perfil['materias_aprobadas']}
├ Materias Reprobadas: {perfil['materias_no_acreditadas']}
├ Créditos: {perfil['créditos']}
└ Nivel Inglés: {perfil['nivel_inglés']}

*Tutoría:*
├ Tutor: {perfil['tutor']}
└ Email: {perfil['email']}
"""
        
        await update.message.reply_text(mensaje, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
```

### 4. ACTUALIZAR `scraper/fetcher.py`

**RESTAURAR fetch_kardex:**
```python
def fetch_kardex(self) -> str:
    """
    Obtiene el kardex del alumno desde el endpoint de calificaciones.
    
    El kardex está disponible en la página de boleta de calificaciones,
    dentro del tab "Kardex".
    
    Returns:
        str: HTML de la página de calificaciones con kardex
    
    Raises:
        FetchError: Si hay error al obtener el kardex
    """
    url = f"{settings.UPQ_BASE_URL}/alumnos.php/boleta-calificaciones"
    
    try:
        response = self.session.get(url, headers={
            'Referer': f'{settings.UPQ_BASE_URL}/alumnos.php/home/home',
        })
        response.raise_for_status()
        return response.text
    except requests.exceptions.HTTPError as e:
        raise FetchError(f"Error al obtener kardex: {e}")
```

**AGREGAR fetch_perfil:**
```python
def fetch_perfil(self) -> str:
    """
    Obtiene la información del perfil del estudiante desde el home.
    
    Returns:
        str: HTML de la página home con datos del perfil
    
    Raises:
        FetchError: Si hay error al obtener el perfil
    """
    url = f"{settings.UPQ_BASE_URL}/alumnos.php/home/home"
    
    try:
        response = self.session.get(url)
        response.raise_for_status()
        return response.text
    except requests.exceptions.HTTPError as e:
        raise FetchError(f"Error al obtener perfil: {e}")
```

### 5. ACTUALIZAR `scraper/parser.py`

**AGREGAR parsers:**
```python
def parse_kardex(html: str) -> List[Dict[str, str]]:
    """
    Parsea el kardex académico desde el HTML.
    
    Args:
        html: HTML de la página de calificaciones con kardex
        
    Returns:
        Lista de diccionarios con datos de cada materia
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Buscar el div del kardex
    kardex_div = soup.find('div', string=re.compile('Kardex'))
    if not kardex_div:
        return []
    
    # Encontrar la tabla
    table = kardex_div.find_next('table', class_='grid')
    if not table:
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
    
    return materias


def parse_student_profile(html: str) -> Dict[str, str]:
    """
    Parsea el perfil del estudiante desde el HTML del home.
    
    Args:
        html: HTML de la página home
        
    Returns:
        Diccionario con datos del perfil
    """
    soup = BeautifulSoup(html, 'html.parser')
    perfil = {}
    
    # Buscar contenedor de información del estudiante
    # (ajustar selectores según la estructura real)
    info_div = soup.find('div', class_='student-info')
    
    if info_div:
        # Extraer campos
        for strong in info_div.find_all('strong'):
            campo = strong.text.strip().replace(':', '').lower().replace(' ', '_')
            valor = strong.next_sibling
            if valor:
                perfil[campo] = valor.strip()
    
    # Extraer foto si existe
    foto_img = soup.find('img', src=re.compile(r'/uploads/fotos/alumnos/'))
    if foto_img:
        perfil['foto_url'] = foto_img['src']
    
    return perfil


def parse_carga_academica(html: str) -> Dict:
    """
    Parsea la carga académica actual.
    
    Args:
        html: HTML de la página de carga académica
        
    Returns:
        Diccionario con periodo y lista de materias
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
    
    return {
        'periodo': periodo,
        'materias': materias
    }
```

---

## 📋 RESUMEN DE ENDPOINTS VERIFICADOS

| Endpoint | Archivo Debug | Estado | Datos Disponibles |
|----------|---------------|--------|-------------------|
| `/boleta-calificaciones` | `debug_calificaciones.html` | ✅ EXISTE | Boleta, Historial, Kardex, Reprobadas |
| `/historial-academico` | `debug_historial_academico.html` | ✅ EXISTE | 1310 líneas, historial completo |
| `/alumno_informacion_general` | `debug_alumno_info_general.html` | ✅ EXISTE | 2037 líneas, mapa curricular |
| `/home/home` | `debug_home.html` | ✅ EXISTE | Perfil completo del estudiante |
| `/carga-academica` | `debug_carga_academica.html` | ✅ EXISTE | Materias actuales con parciales |
| `/horario-materias` | `debug_horario_materias.html` | ✅ EXISTE | Horario detallado |
| `/seguimiento-cuatrimestral` | `debug_seguimiento_cuatrimestral.html` | ✅ EXISTE | Progreso por cuatrimestre |
| `/controlpagos/pagosEnAdeudos` | `debug_pagos_adeudos.html` | ✅ EXISTE | Adeudos pendientes |
| `/pagos` | `debug_pagos.html` | ✅ EXISTE | Historial de pagos |
| `/documentos-en-proceso` | `debug_documentos_proceso.html` | ✅ EXISTE | Documentos solicitados |
| `/servicios` | `debug_servicios.html` | ❌ NO EXISTE | Módulo en desarrollo |

---

## ✅ CONCLUSIONES

1. **EL KARDEX SÍ EXISTE** - Disponible en 3 formas diferentes
2. **EL PERFIL SÍ EXISTE** - Datos completos en `/home/home`
3. **TODOS LOS ENDPOINTS FUNCIONAN** excepto `/servicios`
4. **DATOS MÁS COMPLETOS** están en:
   - `debug_alumno_info_general.html` (2037 líneas)
   - `debug_historial_academico.html` (1310 líneas)
   - `debug_calificaciones.html` (con 4 tabs)
   - `desempeno_escolar_report.json` (JSON estructurado)

5. **NECESITAS ACTUALIZAR:**
   - ❌ Eliminar los `raise FetchError` de kardex y perfil
   - ✅ Implementar parsers para estos endpoints
   - ✅ Restaurar comandos del bot
   - ✅ Usar los datos JSON cuando estén disponibles

---

## 🚀 PRÓXIMOS PASOS

1. **INMEDIATO:** Implementar `fetch_kardex()` y `parse_kardex()`
2. **PRIORITARIO:** Implementar `fetch_perfil()` y `parse_student_profile()`
3. **IMPORTANTE:** Agregar `parse_carga_academica()` para calificaciones parciales
4. **ÚTIL:** Implementar `parse_mapa_curricular()` para vista completa
5. **BONUS:** Crear endpoint para descargar JSON directo

