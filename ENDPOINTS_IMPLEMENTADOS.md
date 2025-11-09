# ENDPOINTS IMPLEMENTADOS - Sistema UPQ

**Fecha:** 9 de noviembre de 2025  
**Estado:** Todos los endpoints verificados están implementados ✅

---

## 📊 RESUMEN EJECUTIVO

### ✅ Implementados y Verificados (14 endpoints)
Todos los endpoints que aparecen en `exploracion_completa_sii.json` con status 200.

### ❌ No Existen en el Sistema
Endpoints solicitados que NO aparecen en la exploración real del sistema.

---

## A. INFORMACIÓN ACADÉMICA 📚

### 1. Home/Perfil Principal ✅
- **Endpoint Real:** `/alumnos.php/home/home`
- **Método Fetch:** `fetch_home_data()`
- **Método Wrapper:** `get_home_data()`
- **Contiene:**
  - Nombre completo
  - Matrícula
  - Carrera y generación
  - Promedio general
  - Créditos (cursados/totales)
  - Materias aprobadas/reprobadas
  - Nivel de inglés
  - Estatus (ACTIVO/INACTIVO)
  - NSS
  - Tutor asignado
  - Foto del alumno

**⚠️ NOTA:** El endpoint `/alumnos.php/perfil` NO EXISTE. Los datos del perfil están en `/home/home`.

---

### 2. Información General - Mapa Curricular ✅
- **Endpoint Real:** `/alumnos.php/alumno_informacion_general?mid=16746`
- **Método Fetch:** `fetch_info_general()`
- **Método Wrapper:** `get_info_general()`
- **Contiene:**
  - Mapa curricular completo (10 cuatrimestres)
  - Todas las materias por ciclo de formación
  - Calificaciones por materia
  - Tipo de evaluación (1-13)
  - Número de intentos por materia
  - Estado: acreditado/no acreditado

---

### 3. Calificaciones - Kardex Completo ✅
- **Endpoint Real:** `/alumnos.php/calificaciones`
- **Método Fetch:** `fetch_kardex()`
- **Método Wrapper:** `get_kardex()`
- **Contiene:**
  - Kardex completo (66 materias)
  - Tabla con: #, Clave, Materia, Cuatrimestre, Calificación, Tipo Evaluación
  - Materias reprobadas (si aplica)
  - Div ID: `kardexContainer`

**⚠️ NOTA:** El endpoint `/alumnos.php/kardex` NO EXISTE. El kardex está en `/calificaciones`.

---

### 4. Boleta de Calificaciones ✅
- **Endpoint Real:** `/alumnos.php/boleta-calificaciones`
- **Método Fetch:** `fetch_boleta()`
- **Método Wrapper:** `get_boleta()`
- **Contiene:**
  - Tabs: "Boleta de Calificaciones", "Historial Académico", "Kardex"
  - Calificaciones por cuatrimestre
  - Promedio del cuatrimestre
  - Créditos obtenidos
  - Formulario para imprimir: `formato-boleta-calificaciones`

---

### 5. Historial Académico ✅
- **Endpoint Real:** `/alumnos.php/historial-academico`
- **Método Fetch:** `fetch_historial_academico()`
- **Método Wrapper:** `get_historial_academico()`
- **Contiene:**
  - Tabla completa de historial (1310 líneas)
  - Columnas: #, Fecha, Ciclo, Clave, Materia, Créditos, Calificación, Tipo Evaluación, Estado
  - Ordenado por fecha de evaluación
  - Incluye cuatrimestre actual

---

### 6. Carga Académica ✅
- **Endpoint Real:** `/alumnos.php/carga-academica?iid={inscription_id}`
- **Método Fetch:** `fetch_carga_academica(inscription_id=None)`
- **Método Wrapper:** `get_carga_academica(inscription_id=None)`
- **Contiene:**
  - Materias del cuatrimestre actual
  - Columnas: #, Clave, Materia, Aula, Grupo, Profesor
  - Calificaciones parciales (P1, P2, P3)
  - Calificaciones finales (PF1, PF2, PF3)
  - Calificación final de la materia
  - Tabla ID: `tblMaterias`

**⚠️ IMPORTANTE:** Requiere parámetro `iid` (inscription ID) - se obtiene dinámicamente al hacer login.

---

### 7. Horario de Clases ✅
- **Endpoint Real:** `/alumnos.php/horario-materias?iid={inscription_id}`
- **Método Fetch:** `fetch_horario(inscription_id=None)`
- **Método Wrapper:** `get_horario(inscription_id=None)`
- **Contiene:**
  - Horario semanal completo
  - Columnas: Día, Hora Inicio, Hora Fin, Aula, Materia, Profesor
  - Formato 24h (08:00:00 - 10:00:00)
  - Ordenado por día y hora

**⚠️ NOTA:** El endpoint `/alumnos.php/horario` NO EXISTE. El horario está en `/horario-materias?iid=`.

---

### 8. Seguimiento Cuatrimestral - Calendario ✅
- **Endpoint Real:** `/alumnos.php/seguimiento-cuatrimestral`
- **Método Fetch:** `fetch_calendario()`
- **Método Wrapper:** `get_calendario()`
- **Contiene:**
  - Progreso por cuatrimestre
  - Promedio de cada cuatrimestre
  - Créditos acumulados por cuatrimestre
  - Estado: CONCLUIDO / EN CURSO
  - Fechas de inicio y fin de cada periodo

**⚠️ NOTA:** El endpoint `/alumnos.php/calendario` NO EXISTE. El calendario está en `/seguimiento-cuatrimestral`.

---

## B. SERVICIOS Y TRÁMITES 🏫

### 9. Servicios Disponibles ✅
- **Endpoint Real:** `/alumnos.php/servicios`
- **Método Fetch:** `fetch_servicios()`
- **Método Wrapper:** `get_servicios()`
- **Contiene:**
  - Servicios disponibles para el alumno
  - **NOTA:** El módulo aún está en desarrollo según debug

**❌ NO IMPLEMENTADOS (No aparecen en exploración):**
- `/alumnos.php/servicio-social` - NO EXISTE
- `/alumnos.php/talleres` - NO EXISTE
- `/alumnos.php/biblioteca` - NO EXISTE

**Recomendación:** Estos servicios podrían estar dentro de `/servicios` o no estar disponibles en el sistema actual.

---

### 10. Inscripción ✅
- **Endpoint Real:** `/alumnos.php/inscripcion`
- **Método Fetch:** `fetch_inscripcion()`
- **Método Wrapper:** `get_inscripcion()`
- **Contiene:**
  - Tabs: "Carga Académica Actual", "Horario de Clases", "Cuatrimestres"
  - Links a: `/carga-academica?iid=`, `/horario-materias?iid=`, `/seguimiento-cuatrimestral`
  - Sistema de navegación con EasyUI

**❌ NO IMPLEMENTADO:**
- `/alumnos.php/reinscripcion` - NO EXISTE en exploración

---

## C. ADMINISTRATIVO 💰

### 11. Pagos - Historial ✅
- **Endpoint Real:** `/alumnos.php/pagos`
- **Método Fetch:** `fetch_pagos()`
- **Método Wrapper:** `get_pagos()`
- **Contiene:**
  - Historial completo de pagos
  - Columnas: Fecha, Folio, Concepto, Monto, Forma de Pago
  - Recibos de pago
  - Conceptos detallados

---

### 12. Pagos en Proceso ✅
- **Endpoint Real:** `/alumnos.php/pagos-en-proceso`
- **Método Fetch:** `fetch_pagos_proceso()`
- **Método Wrapper:** `get_pagos_proceso()`
- **Contiene:**
  - Pagos que están en trámite
  - Documentos relacionados con pagos pendientes
  - Generalmente vacío si no hay trámites activos

---

### 13. Adeudos Pendientes ✅
- **Endpoint Real:** `/alumnos.php/controlpagos/pagosEnAdeudos`
- **Método Fetch:** `fetch_adeudos()`
- **Método Wrapper:** `get_adeudos()`
- **Contiene:**
  - Adeudos pendientes
  - Montos pendientes
  - Conceptos
  - Fechas límite
  - Estado: "No se encontraron registros" si no hay adeudos

**⚠️ NOTA:** El endpoint `/alumnos.php/adeudos` NO EXISTE. Los adeudos están en `/controlpagos/pagosEnAdeudos`.

---

## D. DOCUMENTOS 📄

### 14. Documentos en Proceso ✅
- **Endpoint Real:** `/alumnos.php/documentos-en-proceso`
- **Método Fetch:** `fetch_documentos()`
- **Método Wrapper:** `get_documentos()`
- **Contiene:**
  - Documentos solicitados
  - Columnas: Folio, Documento, Fecha Solicitud, Estado, Fecha Entrega
  - Certificados, constancias, credenciales
  - Estado del trámite

**⚠️ NOTA:** El endpoint `/alumnos.php/documentos` NO EXISTE. Los documentos están en `/documentos-en-proceso`.

---

## 📋 TABLA RESUMEN - TODOS LOS MÉTODOS

### Métodos de la Clase `UPQGradesFetcher`

| # | Método | Endpoint Real | Status | Requiere iid |
|---|--------|---------------|--------|--------------|
| 1 | `fetch_grades_html()` | `/alumnos.php/calificaciones` | ✅ | Opcional |
| 2 | `fetch_home_data()` | `/alumnos.php/home/home` | ✅ | No |
| 3 | `fetch_horario()` | `/alumnos.php/horario-materias?iid=` | ✅ | Sí |
| 4 | `fetch_boleta()` | `/alumnos.php/boleta-calificaciones` | ✅ | No |
| 5 | `fetch_pagos()` | `/alumnos.php/pagos` | ✅ | No |
| 6 | `fetch_adeudos()` | `/alumnos.php/controlpagos/pagosEnAdeudos` | ✅ | No |
| 7 | `fetch_documentos()` | `/alumnos.php/documentos-en-proceso` | ✅ | No |
| 8 | `fetch_calendario()` | `/alumnos.php/seguimiento-cuatrimestral` | ✅ | No |
| 9 | `fetch_kardex()` | `/alumnos.php/calificaciones` | ✅ | No |
| 10 | `fetch_perfil()` | `/alumnos.php/home/home` | ✅ | No |
| 11 | `fetch_historial_academico()` | `/alumnos.php/historial-academico` | ✅ | No |
| 12 | `fetch_carga_academica()` | `/alumnos.php/carga-academica?iid=` | ✅ | Sí |
| 13 | `fetch_pagos_proceso()` | `/alumnos.php/pagos-en-proceso` | ✅ | No |
| 14 | `fetch_inscripcion()` | `/alumnos.php/inscripcion` | ✅ | No |
| 15 | `fetch_info_general()` | `/alumnos.php/alumno_informacion_general` | ✅ | No |
| 16 | `fetch_servicios()` | `/alumnos.php/servicios` | ✅ | No |

### Métodos de la Clase `UPQScraperSession`

| # | Método Wrapper | Método Fetch Correspondiente |
|---|----------------|------------------------------|
| 1 | `get_grades()` | `fetch_grades_html()` |
| 2 | `get_home_data()` | `fetch_home_data()` |
| 3 | `get_horario()` | `fetch_horario()` |
| 4 | `get_boleta()` | `fetch_boleta()` |
| 5 | `get_pagos()` | `fetch_pagos()` |
| 6 | `get_adeudos()` | `fetch_adeudos()` |
| 7 | `get_documentos()` | `fetch_documentos()` |
| 8 | `get_calendario()` | `fetch_calendario()` |
| 9 | `get_kardex()` | `fetch_kardex()` |
| 10 | `get_perfil()` | `fetch_perfil()` |
| 11 | `get_historial_academico()` | `fetch_historial_academico()` |
| 12 | `get_carga_academica()` | `fetch_carga_academica()` |
| 13 | `get_pagos_proceso()` | `fetch_pagos_proceso()` |
| 14 | `get_inscripcion()` | `fetch_inscripcion()` |
| 15 | `get_info_general()` | `fetch_info_general()` |
| 16 | `get_servicios()` | `fetch_servicios()` |

---

## 🔑 PARÁMETROS IMPORTANTES

### 1. Inscription ID (iid)
- **Obtención:** Automática al hacer login vía `authenticator.get_inscription_id()`
- **Usado en:**
  - `fetch_horario()`
  - `fetch_carga_academica()`
- **Detección:** Busca patrón `iid=(\d+)` en HTML de home, inscripciones, carga académica
- **Fallback:** `settings.UPQ_INSCRIPTION_ID` desde `.env`

### 2. Timestamp Cache Busting
- **Formato:** `?_={timestamp_ms}`
- **Generación:** `int(time.time() * 1000)`
- **Usado en:** TODOS los endpoints AJAX

### 3. AJAX Headers
```python
{
    'X-Requested-With': 'XMLHttpRequest',
    'Accept': '*/*',
    'Referer': f'{settings.UPQ_BASE_URL}/alumnos.php/home/home'
}
```

### 4. MID Parameter
- **Valor:** `mid=16746` (puede variar por usuario)
- **Usado en:** `/alumno_informacion_general`

---

## ❌ ENDPOINTS SOLICITADOS QUE NO EXISTEN

### Categoría: Académica
1. **`/alumnos.php/kardex`** → Usar: `/alumnos.php/calificaciones`
2. **`/alumnos.php/horario`** → Usar: `/alumnos.php/horario-materias?iid=`
3. **`/alumnos.php/perfil`** → Usar: `/alumnos.php/home/home`

### Categoría: Administrativa
4. **`/alumnos.php/adeudos`** → Usar: `/alumnos.php/controlpagos/pagosEnAdeudos`
5. **`/alumnos.php/documentos`** → Usar: `/alumnos.php/documentos-en-proceso`
6. **`/alumnos.php/calendario`** → Usar: `/alumnos.php/seguimiento-cuatrimestral`

### Categoría: No Verificados
7. **`/alumnos.php/servicio-social`** - No aparece en exploración
8. **`/alumnos.php/talleres`** - No aparece en exploración
9. **`/alumnos.php/biblioteca`** - No aparece en exploración
10. **`/alumnos.php/reinscripcion`** - No aparece en exploración

**Recomendación:** Estos 4 endpoints pueden:
- Estar dentro del módulo `/servicios`
- No estar implementados en el sistema actual
- Requerir permisos especiales
- Estar disponibles en ciertos periodos del año (reinscripción)

---

## 🚀 USO BÁSICO

```python
from scraper.fetcher import UPQScraperSession

# Crear sesión
scraper = UPQScraperSession('matricula', 'password')

# Login automático
scraper.login()

# Obtener datos (ejemplos)
home = scraper.get_home_data()
kardex = scraper.get_kardex()
horario = scraper.get_horario()  # iid se detecta automáticamente
boleta = scraper.get_boleta()
pagos = scraper.get_pagos()
adeudos = scraper.get_adeudos()
documentos = scraper.get_documentos()
calendario = scraper.get_calendario()
historial = scraper.get_historial_academico()
carga = scraper.get_carga_academica()  # iid se detecta automáticamente
info = scraper.get_info_general()

# Logout
scraper.logout()
```

---

## 📝 NOTAS FINALES

1. **Todos los endpoints verificados están implementados** ✅
2. **El `iid` se obtiene dinámicamente** - No hardcodeado ✅
3. **Los métodos usan AJAX headers correctos** ✅
4. **Todos incluyen timestamp para cache busting** ✅
5. **Manejo de errores con FetchError** ✅
6. **Logging informativo en cada operación** ✅

---

**Última actualización:** 9 de noviembre de 2025  
**Estado:** ✅ COMPLETO - Todos los endpoints verificados implementados
