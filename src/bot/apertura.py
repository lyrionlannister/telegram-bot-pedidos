"""Abierto/cerrado del negocio (editable por el admin con /activar y /desactivar)."""
import json

from .config import config

MENSAJE_FUERA_DE_LINEA = (
    "🔴 Por ahora no estamos recibiendo pedidos. Vuelve a intentarlo más tarde."
)


def _cargar() -> bool:
    p = config.rutas.apertura_path
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))["abierto"]
    return True


_estado = {"abierto": _cargar()}


def _cargar_pendientes() -> set[int]:
    p = config.rutas.pendientes_path
    if p.exists():
        return set(json.loads(p.read_text(encoding="utf-8")))
    return set()


_pendientes = _cargar_pendientes()


def esta_abierto() -> bool:
    return _estado["abierto"]


def set_abierto(valor: bool) -> None:
    _estado["abierto"] = valor
    config.rutas.apertura_path.write_text(
        json.dumps({"abierto": valor}, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def registrar_pendiente(chat_id: int) -> None:
    """Guarda a quien escribió mientras el bot estaba desactivado, para re-contactarlo al activar."""
    _pendientes.add(chat_id)
    config.rutas.pendientes_path.write_text(
        json.dumps(sorted(_pendientes), ensure_ascii=False, indent=2), encoding="utf-8"
    )


def tomar_pendientes() -> list[int]:
    """Devuelve los pendientes y vacía la lista."""
    chat_ids = sorted(_pendientes)
    _pendientes.clear()
    config.rutas.pendientes_path.write_text(
        json.dumps([], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return chat_ids
