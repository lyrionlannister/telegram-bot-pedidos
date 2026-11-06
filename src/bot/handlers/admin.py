"""Botones del administrador (confirmar pago, paquete listo)."""
import html
import json

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from ..apertura import set_abierto, tomar_pendientes
from ..catalogo import CATALOGO, guardar_catalogo
from ..config import HTML, log
from ..constants import EN_REPARTO, ESPERA_PAGO, PIDE_UBICACION, PREPARANDO, REVISION_PAGO
from ..equipo import EQUIPO, admin_chat_id, guardar_equipo, siguiente_repartidor
from ..pagos import DATOS_PAGO, guardar_datos_pago
from ..repository import actualizar, obtener
from ..services import link_mapa, resumen, teclado_ubicacion


def teclado_apertura(abierto: bool) -> InlineKeyboardMarkup:
    if abierto:
        return InlineKeyboardMarkup([[InlineKeyboardButton("🔴 Desactivar", callback_data="bot_off")]])
    return InlineKeyboardMarkup([[InlineKeyboardButton("🟢 Activar", callback_data="bot_on")]])


async def _avisar_pendientes(ctx: ContextTypes.DEFAULT_TYPE) -> int:
    """Reintenta contactar a quienes escribieron mientras el bot estaba desactivado."""
    chat_ids = tomar_pendientes()
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Hacer pedido", callback_data="nuevo")]])
    avisados = 0
    for chat_id in chat_ids:
        try:
            await ctx.bot.send_message(
                chat_id, "🟢 ¡Ya estamos recibiendo pedidos!", reply_markup=kb
            )
            avisados += 1
        except TelegramError as e:
            log.error("No se pudo avisar al chat %s: %s", chat_id, e)
    return avisados


async def cmd_abrir(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id != admin_chat_id():
        return
    set_abierto(True)
    avisados = await _avisar_pendientes(ctx)
    texto = "🟢 Bot activado. Ya se pueden hacer pedidos."
    if avisados:
        texto += f"\nSe avisó a {avisados} cliente(s) que habían escrito mientras estabas desconectado."
    await update.message.reply_text(texto, reply_markup=teclado_apertura(True))


async def cmd_cerrar(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id != admin_chat_id():
        return
    set_abierto(False)
    await update.message.reply_text(
        "🔴 Bot desactivado. No se podrán hacer pedidos nuevos.", reply_markup=teclado_apertura(False)
    )


async def cb_apertura(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if q.message.chat.id != admin_chat_id():
        await q.answer("No autorizado.", show_alert=True)
        return
    abierto = q.data == "bot_on"
    set_abierto(abierto)
    await q.answer("Bot activado ✅" if abierto else "Bot desactivado 🔴")
    texto = "🟢 Bot activado. Ya se pueden hacer pedidos." if abierto else "🔴 Bot desactivado. No se podrán hacer pedidos nuevos."
    if abierto:
        avisados = await _avisar_pendientes(ctx)
        if avisados:
            texto += f"\nSe avisó a {avisados} cliente(s) que habían escrito mientras estabas desconectado."
    await q.edit_message_text(texto, reply_markup=teclado_apertura(abierto))


async def cmd_catalogo(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Permite al admin ver y reemplazar el catálogo completo enviando el JSON."""
    if update.effective_chat.id != admin_chat_id():
        return

    texto = update.message.text.split(maxsplit=1)
    if len(texto) == 1:
        actual = json.dumps(CATALOGO, ensure_ascii=False, indent=2)
        await update.message.reply_text(
            "Catálogo actual:\n<pre>" + html.escape(actual) + "</pre>\n\n"
            "Para reemplazarlo envía:\n/catalogo [JSON de la lista completa]",
            parse_mode=HTML,
        )
        return

    try:
        nuevo = json.loads(texto[1])
        if not isinstance(nuevo, list) or not all(
            isinstance(p, dict) and {"id", "nombre", "precio"} <= p.keys() for p in nuevo
        ):
            raise ValueError("cada producto necesita id, nombre y precio")
    except (json.JSONDecodeError, ValueError) as e:
        await update.message.reply_text(f"JSON inválido: {e}")
        return

    guardar_catalogo(nuevo)
    await update.message.reply_text(f"Catálogo actualizado ✅ ({len(nuevo)} productos)")


async def cmd_pago(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Permite al admin ver y cambiar los datos de pago (JSON: banco, clabe, tarjeta, etc.)."""
    if update.effective_chat.id != admin_chat_id():
        return

    texto = update.message.text.split(maxsplit=1)
    if len(texto) == 1:
        actual = json.dumps(DATOS_PAGO, ensure_ascii=False, indent=2)
        await update.message.reply_text(
            "Datos de pago actuales:\n<pre>" + html.escape(actual) + "</pre>\n\n"
            "Para cambiarlos envía:\n/pago [JSON con los campos]",
            parse_mode=HTML,
        )
        return

    try:
        nuevo = json.loads(texto[1])
        if not isinstance(nuevo, dict) or not nuevo:
            raise ValueError("debe ser un JSON con al menos un campo")
    except (json.JSONDecodeError, ValueError) as e:
        await update.message.reply_text(f"JSON inválido: {e}")
        return

    guardar_datos_pago(nuevo)
    await update.message.reply_text("Datos de pago actualizados ✅")


async def cmd_equipo(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Permite al admin ver y cambiar el admin y la cola de repartidores (JSON)."""
    if update.effective_chat.id != admin_chat_id():
        return

    texto = update.message.text.split(maxsplit=1)
    if len(texto) == 1:
        actual = json.dumps(EQUIPO, ensure_ascii=False, indent=2)
        await update.message.reply_text(
            "Equipo actual:\n<pre>" + html.escape(actual) + "</pre>\n\n"
            "Para cambiarlo envía:\n/equipo [JSON con admin_chat_id y repartidores: "
            '[{"chat_id": ..., "nombre": ..., "activo": true}]]',
            parse_mode=HTML,
        )
        return

    try:
        nuevo = json.loads(texto[1])
        if not isinstance(nuevo, dict) or not {"admin_chat_id", "repartidores"} <= nuevo.keys():
            raise ValueError("debe traer admin_chat_id y repartidores")
        if not isinstance(nuevo["repartidores"], list) or not all(
            isinstance(r, dict) and {"chat_id", "nombre", "activo"} <= r.keys() for r in nuevo["repartidores"]
        ):
            raise ValueError("cada repartidor necesita chat_id, nombre y activo")
        nuevo = {
            "admin_chat_id": int(nuevo["admin_chat_id"]),
            "repartidores": [
                {"chat_id": int(r["chat_id"]), "nombre": str(r["nombre"]), "activo": bool(r["activo"])}
                for r in nuevo["repartidores"]
            ],
        }
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        await update.message.reply_text(f"JSON inválido: {e}")
        return

    guardar_equipo(nuevo)
    await update.message.reply_text("Equipo actualizado ✅")


async def cb_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if q.message.chat.id != admin_chat_id():
        await q.answer("No autorizado.", show_alert=True)
        return

    accion, pid = q.data.split(":")
    p = obtener(int(pid))
    quien = "el administrador"

    if accion in ("pago_ok", "pago_no"):
        if not p or p.estado != REVISION_PAGO:
            await q.answer("Este pedido ya fue revisado.", show_alert=True)
            return

        if accion == "pago_ok":
            actualizar(p.id, estado=PIDE_UBICACION)
            await q.answer("Pago confirmado")
            await q.edit_message_caption(
                caption=(q.message.caption_html or "") + f"\n\n✅ Pago confirmado por {quien}",
                parse_mode=HTML,
            )
            await ctx.bot.send_message(
                p.user_id,
                "✅ ¡Tu pago fue confirmado!\n\nAhora compárteme tu <b>ubicación</b> para la "
                "entrega tocando el botón 📍 de abajo.",
                parse_mode=HTML,
                reply_markup=teclado_ubicacion(),
            )
        else:
            actualizar(p.id, estado=ESPERA_PAGO, comprobante=None)
            await q.answer("Pago rechazado")
            await q.edit_message_caption(
                caption=(q.message.caption_html or "") + f"\n\n❌ Rechazado por {quien}",
                parse_mode=HTML,
            )
            await ctx.bot.send_message(
                p.user_id,
                "⚠️ No pudimos confirmar tu pago. Revisa que el monto y los datos sean correctos "
                "y vuelve a enviar tu comprobante. Si crees que es un error, contáctanos.",
            )

    elif accion == "listo":
        if not p or p.estado != PREPARANDO:
            await q.answer("Este pedido ya fue enviado al repartidor.", show_alert=True)
            return
        rep = siguiente_repartidor()
        if not rep:
            await q.answer("No hay repartidores disponibles ahora mismo.", show_alert=True)
            return
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✅ Entregado", callback_data=f"entregado:{p.id}")]]
        )
        try:
            await ctx.bot.send_location(rep["chat_id"], latitude=p.lat, longitude=p.lon)
            await ctx.bot.send_message(
                rep["chat_id"],
                "🛵 <b>Nueva entrega</b>\n\n" + resumen(p, para_admin=True) + "\n" + link_mapa(p),
                parse_mode=HTML,
                reply_markup=kb,
            )
        except TelegramError as e:
            log.error("No se pudo avisar al repartidor %s: %s", rep["chat_id"], e)
            await q.answer(
                f"No pude escribirle a {rep['nombre']}. ¿Ya le mandó /start al bot?", show_alert=True
            )
            return
        actualizar(p.id, estado=EN_REPARTO, repartidor_id=rep["chat_id"])
        await q.answer(f"Enviado a {rep['nombre']}")
        await q.edit_message_text(
            q.message.text_html + f"\n\n✅ Listo ({quien}) — enviado a {rep['nombre']}",
            parse_mode=HTML,
        )
        await ctx.bot.send_message(p.user_id, "🛵 ¡Tu pedido ya va en camino!")
