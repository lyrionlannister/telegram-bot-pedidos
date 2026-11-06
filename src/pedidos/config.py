"""Configuración de la app, agrupada en dataclasses por función."""
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from telegram.constants import ParseMode

load_dotenv()
HTML = ParseMode.HTML


@dataclass(frozen=True)
class TelegramConfig:
    token: str


@dataclass(frozen=True)
class NegocioConfig:
    nombre: str


@dataclass(frozen=True)
class RutasConfig:
    base: Path
    db_path: Path
    catalogo_path: Path
    datos_pago_path: Path
    equipo_path: Path
    apertura_path: Path
    pendientes_path: Path


@dataclass(frozen=True)
class Config:
    telegram: TelegramConfig
    negocio: NegocioConfig
    rutas: RutasConfig


def cargar_config() -> Config:
    base = Path(__file__).resolve().parent.parent.parent
    return Config(
        telegram=TelegramConfig(
            token=os.environ["BOT_TOKEN"],
        ),
        negocio=NegocioConfig(
            nombre=os.environ.get("NOMBRE_NEGOCIO", "nuestra tienda"),
        ),
        rutas=RutasConfig(
            base=base,
            db_path=base / "pedidos.db",
            catalogo_path=base / "catalogo.json",
            datos_pago_path=base / "datos_pago.json",
            equipo_path=base / "equipo.json",
            apertura_path=base / "apertura.json",
            pendientes_path=base / "pendientes.json",
        ),
    )


config = cargar_config()

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("bot")
