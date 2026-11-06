"""Catálogo de productos (datos estáticos en JSON)."""
import json

from ..config import config

CATALOGO: list[dict] = json.loads(config.rutas.catalogo_path.read_text(encoding="utf-8"))
PRODUCTOS: dict[str, dict] = {p["id"]: p for p in CATALOGO}


def recargar_catalogo() -> None:
    """Relee catalogo.json y actualiza CATALOGO/PRODUCTOS sin romper las referencias ya importadas."""
    nuevo = json.loads(config.rutas.catalogo_path.read_text(encoding="utf-8"))
    CATALOGO.clear()
    CATALOGO.extend(nuevo)
    PRODUCTOS.clear()
    PRODUCTOS.update({p["id"]: p for p in CATALOGO})


def guardar_catalogo(lista: list[dict]) -> None:
    """Escribe la lista en catalogo.json y recarga CATALOGO/PRODUCTOS."""
    config.rutas.catalogo_path.write_text(
        json.dumps(lista, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    recargar_catalogo()
