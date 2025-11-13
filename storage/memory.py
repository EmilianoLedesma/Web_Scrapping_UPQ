"""
Módulo de persistencia de datos.
Guarda snapshots de calificaciones y detecta cambios.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from config.settings import settings


class StorageError(Exception):
    """Error relacionado con almacenamiento."""
    pass


class GradesMemory:
    """
    Clase para manejar la persistencia de calificaciones.
    Guarda snapshots históricos y detecta cambios.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Inicializa el almacenamiento.

        Args:
            storage_path: Ruta del archivo JSON. Si es None, usa el de settings.
        """
        self.storage_path = storage_path or settings.STORAGE_PATH

        # Asegurar que el directorio existe
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Cargar datos existentes o inicializar
        self.data = self._load_or_initialize()

    def _load_or_initialize(self) -> Dict[str, Any]:
        """
        Carga datos existentes o inicializa estructura nueva.

        Returns:
            Diccionario con la estructura de datos.
        """
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"[INFO] Datos cargados desde: {self.storage_path}")
                    return data
            except json.JSONDecodeError as e:
                print(f"[WARN] Error al leer {self.storage_path}: {e}")
                print("   Inicializando nueva estructura de datos")

        # Inicializar estructura vacía
        return {
            "last_check": None,
            "snapshots": [],
            "changes_detected": []
        }

    def save(self) -> None:
        """
        Guarda los datos en el archivo JSON.

        Raises:
            StorageError: Si hay error al guardar.
        """
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            print(f"[INFO] Datos guardados en: {self.storage_path}")
        except Exception as e:
            raise StorageError(f"Error al guardar datos: {str(e)}")

    def add_snapshot(self, grades_data: Dict[str, Any]) -> None:
        """
        Agrega un nuevo snapshot de calificaciones.

        Args:
            grades_data: Datos de calificaciones parseadas.
        """
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "data": grades_data
        }

        self.data["snapshots"].append(snapshot)
        self.data["last_check"] = snapshot["timestamp"]

        # Limitar a los últimos 50 snapshots para no llenar demasiado
        if len(self.data["snapshots"]) > 50:
            self.data["snapshots"] = self.data["snapshots"][-50:]

        print(f"[INFO] Snapshot guardado: {snapshot['timestamp']}")

    def get_last_snapshot(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene el último snapshot guardado.

        Returns:
            Diccionario con el snapshot o None si no hay snapshots.
        """
        if self.data["snapshots"]:
            return self.data["snapshots"][-1]
        return None

    def detect_changes(self, new_grades: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detecta cambios entre el último snapshot y las nuevas calificaciones.

        Args:
            new_grades: Nuevas calificaciones parseadas.

        Returns:
            Lista de cambios detectados.
        """
        last_snapshot = self.get_last_snapshot()

        if not last_snapshot:
            print("[INFO] No hay snapshot previo - Todos los datos son nuevos")
            return []

        old_grades = last_snapshot.get("data", {})
        changes = []

        # Comparar calificaciones materia por materia
        old_materias = {m["nombre"]: m for m in old_grades.get("materias", [])}
        new_materias = {m["nombre"]: m for m in new_grades.get("materias", [])}

        for materia_nombre, new_materia in new_materias.items():
            old_materia = old_materias.get(materia_nombre)

            if not old_materia:
                # Materia nueva
                changes.append({
                    "timestamp": datetime.now().isoformat(),
                    "tipo": "materia_nueva",
                    "materia": materia_nombre,
                    "datos": new_materia
                })
                continue

            # Comparar calificaciones parcial por parcial
            old_calif = old_materia.get("calificaciones", {})
            new_calif = new_materia.get("calificaciones", {})

            for parcial, new_value in new_calif.items():
                old_value = old_calif.get(parcial)

                # Detectar cambio
                if old_value != new_value:
                    # Solo reportar si el nuevo valor no es None
                    if new_value is not None:
                        changes.append({
                            "timestamp": datetime.now().isoformat(),
                            "tipo": "calificacion_actualizada",
                            "materia": materia_nombre,
                            "parcial": parcial,
                            "calificacion_anterior": old_value,
                            "calificacion_nueva": new_value
                        })

        # Guardar cambios detectados en el historial
        if changes:
            self.data["changes_detected"].extend(changes)

            # Limitar historial de cambios a los últimos 100
            if len(self.data["changes_detected"]) > 100:
                self.data["changes_detected"] = self.data["changes_detected"][-100:]

        return changes

    def get_all_changes(self) -> List[Dict[str, Any]]:
        """
        Obtiene todos los cambios detectados históricamente.

        Returns:
            Lista de todos los cambios.
        """
        return self.data["changes_detected"]

    def get_recent_changes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtiene los cambios más recientes.

        Args:
            limit: Número máximo de cambios a retornar.

        Returns:
            Lista de cambios recientes.
        """
        return self.data["changes_detected"][-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del almacenamiento.

        Returns:
            Diccionario con estadísticas.
        """
        return {
            "total_snapshots": len(self.data["snapshots"]),
            "total_changes": len(self.data["changes_detected"]),
            "last_check": self.data["last_check"],
            "first_snapshot": (
                self.data["snapshots"][0]["timestamp"]
                if self.data["snapshots"]
                else None
            )
        }

    def clear_history(self) -> None:
        """Limpia todo el historial (usar con precaución)."""
        self.data = {
            "last_check": None,
            "snapshots": [],
            "changes_detected": []
        }
        self.save()
        print("[INFO] Historial limpiado")

    def export_to_json(self, filepath: str) -> None:
        """
        Exporta los datos a un archivo JSON externo.

        Args:
            filepath: Ruta del archivo de exportación.
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            print(f"[INFO] Datos exportados a: {filepath}")
        except Exception as e:
            raise StorageError(f"Error al exportar datos: {str(e)}")

    def get_grades_summary(self, grades_data: Dict[str, Any]) -> str:
        """
        Genera un resumen legible de las calificaciones.

        Args:
            grades_data: Datos de calificaciones.

        Returns:
            String con el resumen formateado.
        """
        lines = []
        lines.append("=" * 80)
        lines.append(f"CALIFICACIONES - {grades_data.get('alumno', 'N/A')}")
        lines.append(f"Matrícula: {grades_data.get('matricula', 'N/A')}")
        lines.append(f"Periodo: {grades_data.get('periodo', 'N/A')}")
        lines.append(f"Consulta: {grades_data.get('fecha_consulta', 'N/A')}")
        lines.append("=" * 80)
        lines.append("")

        for materia in grades_data.get("materias", []):
            lines.append(f"Materia: {materia['nombre']}")
            if materia.get('profesor'):
                lines.append(f"   Profesor: {materia['profesor']}")
            if materia.get('grupo'):
                lines.append(f"   Grupo: {materia['grupo']}")

            # Calificaciones
            calificaciones = materia.get('calificaciones', {})
            calif_str = "   Calificaciones: "
            calif_items = []
            for parcial in sorted(calificaciones.keys()):
                valor = calificaciones[parcial]
                if valor is not None:
                    calif_items.append(f"{parcial}: {valor}")
                else:
                    calif_items.append(f"{parcial}: --")

            calif_str += " | ".join(calif_items) if calif_items else "Sin calificaciones"
            lines.append(calif_str)
            lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)

    def format_changes(self, changes: List[Dict[str, Any]]) -> str:
        """
        Formatea cambios para mostrar al usuario.

        Args:
            changes: Lista de cambios.

        Returns:
            String con los cambios formateados.
        """
        if not changes:
            return "[OK] No hay cambios detectados"

        lines = []
        lines.append("=" * 80)
        lines.append(f"CAMBIOS DETECTADOS ({len(changes)})")
        lines.append("=" * 80)
        lines.append("")

        for change in changes:
            tipo = change.get("tipo", "desconocido")

            if tipo == "materia_nueva":
                lines.append(f"[NUEVO] Nueva materia: {change['materia']}")

            elif tipo == "calificacion_actualizada":
                materia = change['materia']
                parcial = change['parcial']
                anterior = change['calificacion_anterior']
                nueva = change['calificacion_nueva']

                anterior_str = str(anterior) if anterior is not None else "--"
                nueva_str = str(nueva)

                lines.append(f"[CAMBIO] {materia}")
                lines.append(f"   {parcial}: {anterior_str} -> {nueva_str}")
                lines.append(f"   Timestamp: {change['timestamp']}")

            lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)
