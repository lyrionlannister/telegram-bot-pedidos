"""Manejador global de errores."""
from telegram.error import NetworkError
from telegram.ext import ContextTypes

from ..config import log


async def on_error(update: object, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if isinstance(ctx.error, NetworkError):
        log.warning("Se cortó la conexión con Telegram, reintentando solo: %s", ctx.error)
        return
    log.exception("Error procesando update", exc_info=ctx.error)
