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


def esta_abierto() -> bool:
    return _estado["abierto"]


def set_abierto(valor: bool) -> None:
    _estado["abierto"] = valor
    config.rutas.apertura_path.write_text(
        json.dumps({"abierto": valor}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
