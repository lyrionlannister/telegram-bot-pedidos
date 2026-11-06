"""
Bot de pedidos para Telegram.

Flujo:
  Cliente: /start -> catálogo -> arma su pedido -> nombre -> teléfono
           -> datos de pago -> envía comprobante
  Admin:   confirma o rechaza el pago
  Cliente: comparte su ubicación
  Admin:   prepara el paquete y toca "Paquete listo"
  Repartidor: hay una cola de repartidores (/conectar, /desconectar). El
              "Paquete listo" se manda al primero disponible y ese pasa
              al final de la cola. Al tocar "Entregado" debe mandar la
              ubicación de la entrega + un texto para confirmarla

Los pedidos se guardan en SQLite (pedidos.db) vía SQLAlchemy, así que si
el bot se reinicia no se pierde en qué paso va cada cliente.
"""

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    TypeHandler,
    filters,
)
from telegram.request import HTTPXRequest, RequestData

from bot.config import config, log
from bot.equipo import es_repartidor
from bot.handlers import admin, cliente, errors, repartidor
from bot.repository import init_db


class FiltroRepartidor(filters.MessageFilter):
    def filter(self, message):
        return es_repartidor(message.chat.id)


class LoggingRequest(HTTPXRequest):
    async def post(self, url: str, request_data: RequestData | None = None, **kwargs):
        chat_id = request_data.parameters.get("chat_id") if request_data else None
        log.info("-> %s chat=%s", url.rsplit("/", 1)[-1], chat_id)
        return await super().post(url, request_data, **kwargs)


async def log_entrante(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    log.info("<- update de %s", user.id if user else "?")


def main() -> None:
    init_db()
    app = Application.builder().token(config.telegram.token).request(LoggingRequest()).build()
    privado = filters.ChatType.PRIVATE

    app.add_handler(TypeHandler(Update, log_entrante), group=-1)
    app.add_handler(CommandHandler("start", cliente.cmd_start, filters=privado))
    app.add_handler(CommandHandler("cancelar", cliente.cmd_cancelar, filters=privado))
    app.add_handler(CommandHandler("catalogo", admin.cmd_catalogo))
    app.add_handler(CommandHandler("pago", admin.cmd_pago))
    app.add_handler(CommandHandler("activar", admin.cmd_abrir))
    app.add_handler(CommandHandler("desactivar", admin.cmd_cerrar))
    app.add_handler(CommandHandler("equipo", admin.cmd_equipo))
    app.add_handler(CommandHandler("conectar", repartidor.cmd_disponible))
    app.add_handler(CommandHandler("desconectar", repartidor.cmd_ocupado))
    app.add_handler(CallbackQueryHandler(cliente.cb_cliente, pattern=r"^(nuevo|add:.+|vaciar|terminar|cancelar)$"))
    app.add_handler(CallbackQueryHandler(admin.cb_admin, pattern=r"^(pago_ok|pago_no|listo):\d+$"))
    app.add_handler(CallbackQueryHandler(repartidor.cb_repartidor, pattern=r"^entregado:\d+$"))
    app.add_handler(CallbackQueryHandler(admin.cb_apertura, pattern=r"^bot_(on|off)$"))
    app.add_handler(CallbackQueryHandler(repartidor.cb_disponibilidad, pattern=r"^rep_(on|off)$"))
    app.add_handler(
        MessageHandler(
            FiltroRepartidor() & privado & ~filters.COMMAND,
            repartidor.en_mensaje_repartidor,
        )
    )
    app.add_handler(MessageHandler(privado & ~filters.COMMAND, cliente.en_mensaje))
    app.add_error_handler(errors.on_error)

    log.info("Bot corriendo…")
    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        log.info("Bot detenido (Ctrl+C).")


if __name__ == "__main__":
    main()
