# 📊 ESTRUCTURA HTML DE ENDPOINTS - ANÁLISIS DE DEBUG FILES

> **Documento técnico**: Estructura real del HTML devuelto por cada endpoint del SII  
> **Fecha**: 9 de noviembre de 2025  
> **Fuente**: Archivos debug_*.html generados durante scraping real

---

## 🎯 PROPÓSITO

Este documento detalla la estructura HTML REAL de cada endpoint, basándose en los archivos debug guardados durante el scraping. Es una referencia para desarrollar parsers precisos.

---

## 📋 ENDPOINTS ANALIZADOS

### 1. **Pagos - `/alumnos.php/pagos`**

**Archivo**: `debug_pagos_historial.html`

**Estructura**:
```html
<div class="easyui-tabs" fit="true">
  <div title="Pagos en Proceso">...</div>
  <div title="Pagos Realizados" class="padding">
    <div class="grid max_height">
      <table cellspacing="1" class="grid" style="width:100%">
        <thead>
          <tr>
            <th>#</th>
            <th>Fecha Pago</th>
            <th>Clave Referencia</th>
            <th>Concepto</th>
            <th>Tipo Pago</th>
            <th>Monto</th>
            <th>Guía CIE</th>
            <th>No. Recibo</th>
          </tr>
        </thead>
        <tr class="row0" id="399365">
          <td>1</td>
          <td class="t-ac">29/09/2025</td>
          <td class="t-al">32712304624443727230</td>
          <td class="t-al">CONSTANCIA DE ESTUDIOS</td>
          <td class="t-ac">TARJETA DE CREDITO</td>
          <td class="t-ar">$94.00</td>
          <td class="t-ar">663607</td>
          <td class="t-ac">0</td>
        </tr>
      </table>
    </div>
  </div>
</div>
```

**Datos importantes**:
- Las filas alternan entre `class="row0"` y `class="row1"`
- Fecha formato: DD/MM/YYYY
- Monto formato: $X.XX
- Tipos de pago observados: "TARJETA DE CREDITO"
- Conceptos: "CONSTANCIA DE ESTUDIOS", "KARDEX", etc.

**Parser recomendado**:
```python
def parse_pagos(html):
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', class_='grid')
    pagos = []
    
    for row in table.find_all('tr', class_=['row0', 'row1']):
        cols = row.find_all('td')
        if len(cols) >= 8:
            pago = {
                'numero': cols[0].get_text(strip=True),
                'fecha': cols[1].get_text(strip=True),
                'referencia': cols[2].get_text(strip=True),
                'concepto': cols[3].get_text(strip=True),
                'tipo_pago': cols[4].get_text(strip=True),
                'monto': cols[5].get_text(strip=True),
                'guia_cie': cols[6].get_text(strip=True),
                'recibo': cols[7].get_text(strip=True)
            }
            pagos.append(pago)
    
    return pagos
```

---

### 2. **Horario - `/alumnos.php/horario-materias?iid={iid}`**

**Archivo**: `debug_horario_materias.html`

**Estructura**:
```html
<div class="frame-auto">
  <h4 class="title">HORARIO DE CLASES: SEPTIEMBRE-DICIEMBRE 2025</h4>
  <div class="grid" style="width:900px">
    <table cellspacing="1" class="grid" id="tblMaterias">
      <thead>
        <tr>
          <th>#</th>
          <th>Clave</th>
          <th>Asignatura</th>
          <th>Aula</th>
          <th>Grupo</th>
          <th>Profesor</th>
        </tr>
      </thead>
      <tr class="row0" id="104890">
        <td>1</td>
        <td></td>
        <td>LIDERAZGO DE EQUIPOS DE ALTO DESEMPEÑO</td>
        <td>C104</td>
        <td>S204-7</td>
        <td>RAMIREZ RESENDIZ ADRIANA KARINA</td>
      </tr>
    </table>
  </div>
</div>
```

**Datos importantes**:
- Título del periodo en `<h4 class="title">`
- Tabla con `id="tblMaterias"`
- Campo "Clave" generalmente vacío
- Aulas formato: C104, Lab3, etc.
- Grupos formato: S204-7

**Nota importante**: ⚠️ Esta tabla NO incluye horarios (días/horas), solo lista las materias.  
Para el horario completo con días y horas, probablemente hay otra sección o endpoint.

**Parser recomendado**:
```python
def parse_horario(html):
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extraer periodo
    titulo = soup.find('h4', class_='title')
    periodo = titulo.get_text(strip=True) if titulo else "No disponible"
    
    # Extraer materias
    table = soup.find('table', id='tblMaterias')
    materias = []
    
    for row in table.find_all('tr', class_=['row0', 'row1']):
        cols = row.find_all('td')
        if len(cols) >= 6:
            materia = {
                'asignatura': cols[2].get_text(strip=True),
                'aula': cols[3].get_text(strip=True),
                'grupo': cols[4].get_text(strip=True),
                'profesor': cols[5].get_text(strip=True)
            }
            materias.append(materia)
    
    return {'periodo': periodo, 'materias': materias}
```

---

### 3. **Adeudos - `/alumnos.php/controlpagos/pagosEnAdeudos`**

**Archivo**: `debug_pagos_adeudos.html`

**Estructura (sin adeudos)**:
```html
<div style="height:auto">
  <div class="grid max_height">
    <table cellspacing="1" class="grid" style="width:100%">
      <thead>
        <tr>
          <th>#</th>
          <th>Fecha Emisión</th>
          <th>Fecha Vencimiento</th>
          <th>Clave Referencia</th>
          <th>Concepto</th>
          <th>Monto</th>
        </tr>
      </thead>
      <tr class="row0">
        <td>&nbsp;</td>
        <td colspan="7">No se encontraron registros</td>
      </tr>
    </table>
  </div>
  <div><label>Total de registros: </label>0</div>
</div>
```

**Datos importantes**:
- Mensaje especial cuando no hay adeudos: "No se encontraron registros"
- Total de registros al final: `<div><label>Total de registros: </label>0</div>`

**Parser recomendado**:
```python
def parse_adeudos(html):
    soup = BeautifulSoup(html, 'html.parser')
    
    # Verificar si hay mensaje de "no encontrados"
    no_registros = soup.find('td', string=lambda x: x and 'No se encontraron registros' in x)
    if no_registros:
        return {'tiene_adeudos': False, 'mensaje': '✅ No tienes adeudos pendientes', 'adeudos': []}
    
    # Si hay registros, parsear tabla
    table = soup.find('table', class_='grid')
    adeudos = []
    
    for row in table.find_all('tr', class_=['row0', 'row1']):
        cols = row.find_all('td')
        if len(cols) >= 6:
            adeudo = {
                'fecha_emision': cols[1].get_text(strip=True),
                'fecha_vencimiento': cols[2].get_text(strip=True),
                'referencia': cols[3].get_text(strip=True),
                'concepto': cols[4].get_text(strip=True),
                'monto': cols[5].get_text(strip=True)
            }
            adeudos.append(adeudo)
    
    return {'tiene_adeudos': True, 'adeudos': adeudos}
```

---

### 4. **Documentos en Proceso - `/alumnos.php/documentos-en-proceso`**

**Archivo**: `debug_documentos_proceso.html`

**Estructura (sin documentos)**:
```html
<div style="height:auto">
  <div class="grid max_height" style="width:900px">
    <table cellspacing="1" class="grid" style="width:100%">
      <thead>
        <tr>
          <th>#</th>
          <th>Descargar</th>
          <th>Fecha de Emisión</th>
          <th>Concepto</th>
        </tr>
      </thead>
      <tr class="row0">
        <td>&nbsp;</td>
        <td colspan="7">No se encontraron registros</td>
      </tr>
    </table>
  </div>
  <div><label>Total de registros: </label>0</div>
</div>
```

**Datos importantes**:
- Igual que adeudos, mensaje "No se encontraron registros" cuando está vacío
- Columna "Descargar" probablemente contiene link de descarga cuando hay documentos

**Parser recomendado**:
```python
def parse_documentos(html):
    soup = BeautifulSoup(html, 'html.parser')
    
    no_registros = soup.find('td', string=lambda x: x and 'No se encontraron registros' in x)
    if no_registros:
        return {'tiene_documentos': False, 'mensaje': 'ℹ️ No tienes documentos en proceso', 'documentos': []}
    
    table = soup.find('table', class_='grid')
    documentos = []
    
    for row in table.find_all('tr', class_=['row0', 'row1']):
        cols = row.find_all('td')
        if len(cols) >= 4:
            doc = {
                'fecha_emision': cols[2].get_text(strip=True),
                'concepto': cols[3].get_text(strip=True),
                'enlace_descarga': cols[1].find('a')['href'] if cols[1].find('a') else None
            }
            documentos.append(doc)
    
    return {'tiene_documentos': True, 'documentos': documentos}
```

---

### 5. **Seguimiento Cuatrimestral - `/alumnos.php/seguimiento-cuatrimestral`**

**Archivo**: `debug_seguimiento_cuatrimestral.html`

**Estructura**:
```html
<h4 class="title">Historial de Cuatrimestres Cursados</h4>
<div class="grid" style="width:900px">
  <table cellspacing="1" class="grid" id="tblCuatrimestres">
    <thead>
      <tr>
        <th>#</th>
        <th>Matricula</th>
        <th>Periodo</th>
        <th>Tipo Inscripción</th>
        <th>Carrera</th>
        <th>Grupo</th>
        <th>Cuatrimestre</th>
        <th>Total Materias</th>
        <th>Promedio</th>
        <th>Estatus</th>
      </tr>
    </thead>
    <tr class="row0" id="131516">
      <td>1</td>
      <td class="t-ac">123046244</td>
      <td class="t-al">SEPTIEMBRE - DICIEMBRE 2023</td>
      <td class="t-ac" title="Nuevo Ingreso">NI</td>
      <td class="t-ac">SISTEMAS</td>
      <td class="t-ac">S204</td>
      <td class="t-ac">1</td>
      <td class="t-ac">7</td>
      <td class="t-ac">9.14</td>
      <td class="t-ac" title="NUEVO INGRESO">NI</td>
    </tr>
  </table>
</div>
```

**Datos importantes**:
- ⭐ **MUY COMPLETO**: Historial completo de todos los cuatrimestres cursados
- Tabla con `id="tblCuatrimestres"`
- Datos por cuatrimestre: periodo, tipo inscripción, materias, promedio, estatus
- Los atributos `title` de los `<td>` contienen descripciones completas:
  - `title="Nuevo Ingreso"` → NI
  - `title="Reinscripción"` → RI
  - `title="ACTIVO"` → A
  - `title="NUEVO INGRESO"` → NI

**Ejemplo de datos reales**:
```
Cuatrimestre 1: SEPTIEMBRE - DICIEMBRE 2023, 7 materias, Promedio: 9.14
Cuatrimestre 2: ENERO-ABRIL 2024, 7 materias, Promedio: 8.86
Cuatrimestre 3: MAYO - AGOSTO 2024, 6 materias, Promedio: 9.17
Cuatrimestre 4: SEPTIEMBRE - DICIEMBRE 2024, 5 materias, Promedio: 9.20
Cuatrimestre 5: ENERO - ABRIL 2025, 7 materias, Promedio: 8.29
```

**Parser recomendado**:
```python
def parse_seguimiento(html):
    soup = BeautifulSoup(html, 'html.parser')
    
    table = soup.find('table', id='tblCuatrimestres')
    cuatrimestres = []
    
    for row in table.find_all('tr', class_=['row0', 'row1']):
        cols = row.find_all('td')
        if len(cols) >= 10:
            cuatrimestre = {
                'numero': cols[0].get_text(strip=True),
                'matricula': cols[1].get_text(strip=True),
                'periodo': cols[2].get_text(strip=True),
                'tipo_inscripcion': cols[3].get_text(strip=True),
                'tipo_inscripcion_desc': cols[3].get('title', ''),
                'carrera': cols[4].get_text(strip=True),
                'grupo': cols[5].get_text(strip=True),
                'cuatrimestre_num': cols[6].get_text(strip=True),
                'total_materias': cols[7].get_text(strip=True),
                'promedio': cols[8].get_text(strip=True),
                'estatus': cols[9].get_text(strip=True),
                'estatus_desc': cols[9].get('title', '')
            }
            cuatrimestres.append(cuatrimestre)
    
    return cuatrimestres
```

---

### 6. **Boleta de Calificaciones - `/alumnos.php/boleta-calificaciones`**

**Archivo**: `debug_boleta_calificaciones.html`

**Estructura**:
```html
<div class="grid max_height">
  <table cellspacing="1" class="grid">
    <thead>
      <tr>
        <th>&nbsp;</th>
        <th colspan="2">Materia Cursadas</th>
        <th colspan="4">Resultados</th>
      </tr>
      <tr>
        <th>#</th>
        <th>Fecha</th>
        <th>Materia</th>
        <th>% Unidades Aprobadas</th>
        <th>Calificación</th>
        <th>Tipo Evaluación</th>
        <th>Observaciones</th>
      </tr>
    </thead>
    <tr class="row0" id="1046437">
      <td>1</td>
      <td>14/04/2025</td>
      <td class="t-al">MATEMÁTICAS PARA INGENIERÍA I</td>
      <td class="t-ac">100</td>
      <td class="t-ac">7</td>
      <td class="t-ac" title="EVALUACION FINAL CURSO ORDINARIO">2</td>
      <td>&nbsp;</td>
    </tr>
  </table>
</div>
```

**Datos importantes**:
- Dos filas de encabezado (merged headers)
- Fecha de evaluación
- % Unidades Aprobadas (generalmente 100)
- Tipo de evaluación con código numérico y descripción en `title`:
  - 1 = "CURSO ORDINARIO"
  - 2 = "EVALUACION FINAL CURSO ORDINARIO"
- Calificaciones numéricas (7, 8, 9, 10, etc.)

**Parser recomendado**:
```python
def parse_boleta(html):
    soup = BeautifulSoup(html, 'html.parser')
    
    table = soup.find('table', class_='grid')
    materias = []
    
    for row in table.find_all('tr', class_=['row0', 'row1']):
        cols = row.find_all('td')
        if len(cols) >= 7:
            materia = {
                'numero': cols[0].get_text(strip=True),
                'fecha': cols[1].get_text(strip=True),
                'nombre': cols[2].get_text(strip=True),
                'porcentaje_aprobado': cols[3].get_text(strip=True),
                'calificacion': cols[4].get_text(strip=True),
                'tipo_evaluacion_codigo': cols[5].get_text(strip=True),
                'tipo_evaluacion': cols[5].get('title', ''),
                'observaciones': cols[6].get_text(strip=True)
            }
            materias.append(materia)
    
    return materias
```

---

## 🎯 PATRONES COMUNES IDENTIFICADOS

### Clases CSS
- `class="grid"` - Tablas de datos
- `class="row0"` y `class="row1"` - Filas alternadas
- `class="t-ac"` - Text align center
- `class="t-al"` - Text align left
- `class="t-ar"` - Text align right
- `class="title"` - Títulos de sección

### IDs importantes
- `id="tblMaterias"` - Tabla de horario
- `id="tblCuatrimestres"` - Tabla de seguimiento cuatrimestral

### Mensaje de vacío
Cuando no hay registros:
```html
<tr class="row0">
  <td>&nbsp;</td>
  <td colspan="7">No se encontraron registros</td>
</tr>
```

### Total de registros
```html
<div><label>Total de registros: </label>0</div>
```

---

## 📊 RESUMEN DE CALIDAD DE DATOS

| Endpoint | Calidad HTML | Datos Completos | Facilidad de Parsing | Notas |
|----------|--------------|-----------------|---------------------|-------|
| Pagos | ⭐⭐⭐⭐⭐ | ✅ | Fácil | Estructura muy limpia |
| Horario | ⭐⭐⭐⭐ | ⚠️ Parcial | Fácil | **NO incluye días/horas** |
| Adeudos | ⭐⭐⭐⭐⭐ | ✅ | Fácil | Mensaje claro cuando vacío |
| Documentos | ⭐⭐⭐⭐⭐ | ✅ | Fácil | Mensaje claro cuando vacío |
| Seguimiento | ⭐⭐⭐⭐⭐ | ✅ | Fácil | **Datos muy completos** |
| Boleta | ⭐⭐⭐⭐ | ✅ | Media | Headers merged |

---

## ⚠️ HALLAZGOS IMPORTANTES

1. **Horario incompleto**: La tabla de `/horario-materias` solo lista materias, aulas y profesores, pero NO incluye los días de la semana ni horarios específicos. Posiblemente hay otra sección del HTML o necesita JavaScript para cargar esa información.

2. **Mensajes vacíos consistentes**: Todos los endpoints usan el mismo patrón para indicar "sin datos": `<td colspan="7">No se encontraron registros</td>`

3. **Atributos title útiles**: Muchos campos usan `title` para descripciones largas (tipo inscripción, tipo evaluación, estatus)

4. **Formato de fechas**: DD/MM/YYYY consistente

5. **Seguimiento cuatrimestral es oro**: Este endpoint tiene datos MUY completos del historial académico completo

---

## 🚀 PRÓXIMOS PASOS RECOMENDADOS

1. ✅ Usar estos parsers para mejorar visualización en bot y CLI
2. ⚠️ Investigar cómo obtener días/horas del horario (puede requerir más scraping)
3. ✅ Implementar detección de "No se encontraron registros" en todos los comandos
4. ✅ Aprovechar el endpoint de seguimiento cuatrimestral para análisis de progreso
5. ✅ Mostrar descripciones completas usando atributos `title`

---

**Fin del documento**
