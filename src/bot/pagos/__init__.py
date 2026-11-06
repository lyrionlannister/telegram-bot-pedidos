"""Datos de pago (JSON editable por el admin con /pago)."""
import json

from ..config import config

_DEFAULT = {
    "banco": "X",
    "clabe": "000000000000000000",
    "tarjeta": "0000 0000 0000 0000",
    "a_nombre_de": "Tu Negocio",
}


def _cargar() -> dict:
    p = config.rutas.datos_pago_path
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return dict(_DEFAULT)


DATOS_PAGO: dict = _cargar()


def guardar_datos_pago(nuevo: dict) -> None:
    config.rutas.datos_pago_path.write_text(
        json.dumps(nuevo, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    DATOS_PAGO.clear()
    DATOS_PAGO.update(nuevo)


def texto_datos_pago() -> str:
    return "\n".join(f"{campo.replace('_', ' ').capitalize()}: {valor}" for campo, valor in DATOS_PAGO.items())
