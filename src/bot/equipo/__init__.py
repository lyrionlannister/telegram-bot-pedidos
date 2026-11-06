"""Chat IDs del admin y repartidores (JSON editable por el admin con /equipo).

Los repartidores forman una cola: al asignar una entrega se toma el primero
disponible y se manda al final, para repartir el trabajo por turnos.
"""
import json

from ..config import config


def _cargar() -> dict:
    p = config.rutas.equipo_path
    if p.exists():
        datos = json.loads(p.read_text(encoding="utf-8"))
        if "repartidores" not in datos:
            datos["repartidores"] = [
                {"chat_id": datos.pop("repartidor_chat_id"), "nombre": "Repartidor", "activo": True}
            ]
        return datos
    # Sin equipo.json todavía: el bot arranca igual (para loguear los chat_id
    # de quien escriba) pero admin_chat_id() fallará hasta que se cree el archivo a mano.
    return {"admin_chat_id": None, "repartidores": []}


EQUIPO: dict = _cargar()


def _guardar() -> None:
    config.rutas.equipo_path.write_text(
        json.dumps(EQUIPO, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def guardar_equipo(nuevo: dict) -> None:
    EQUIPO.clear()
    EQUIPO.update(nuevo)
    _guardar()


def admin_chat_id() -> int:
    return int(EQUIPO["admin_chat_id"])


def repartidores() -> list[dict]:
    return EQUIPO.setdefault("repartidores", [])


def es_repartidor(chat_id: int) -> bool:
    return any(r["chat_id"] == chat_id for r in repartidores())


def set_disponibilidad(chat_id: int, activo: bool) -> bool:
    for r in repartidores():
        if r["chat_id"] == chat_id:
            r["activo"] = activo
            _guardar()
            return True
    return False


def siguiente_repartidor() -> dict | None:
    """Toma el primer repartidor activo de la cola y lo manda al final."""
    lista = repartidores()
    for i, r in enumerate(lista):
        if r.get("activo"):
            lista.append(lista.pop(i))
            _guardar()
            return lista[-1]
    return None
