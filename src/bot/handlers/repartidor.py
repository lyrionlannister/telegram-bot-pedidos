"""Botones y mensajes del repartidor (marcar entregado con ubicación y nota obligatorias)."""
import html

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import ContextTypes

from ..config import HTML
from ..equipo import admin_chat_id, es_repartidor, set_disponibilidad
from ..pedidos.constants import CONFIRMANDO_ENTREGA, EN_REPARTO, ENTREGADO
from ..pedidos.repository import actualizar, obtener, pedido_en_confirmacion


def teclado_disponibilidad(activo: bool) -> InlineKeyboardMarkup:
    if activo:
        return InlineKeyboardMarkup([[InlineKeyboardButton("🔕 Desconectar", callback_data="rep_off")]])
    return InlineKeyboardMarkup([[InlineKeyboardButton("🟢 Conectar", callback_data="rep_on")]])


async def cmd_disponible(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not set_disponibilidad(update.effective_chat.id, True):
        return
    await update.message.reply_text(
        "✅ Estás disponible. Entrarás a la cola de entregas.",
        reply_markup=teclado_disponibilidad(True),
    )


async def cmd_ocupado(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not set_disponibilidad(update.effective_chat.id, False):
        return
    await update.message.reply_text(
        "🔕 Ya no recibirás nuevas entregas.",
        reply_markup=teclado_disponibilidad(False),
    )


async def cb_disponibilidad(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not es_repartidor(q.message.chat.id):
        await q.answer("No autorizado.", show_alert=True)
        return
    activo = q.data == "rep_on"
    set_disponibilidad(q.message.chat.id, activo)
    await q.answer("Conectado ✅" if activo else "Desconectado 🔕")
    await q.edit_message_text(
        "✅ Estás disponible. Entrarás a la cola de entregas." if activo else "🔕 Ya no recibirás nuevas entregas.",
        reply_markup=teclado_disponibilidad(activo),
    )


def teclado_ubicacion_entrega() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📍 Enviar ubicación de entrega", request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def cb_repartidor(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not es_repartidor(q.message.chat.id):
        await q.answer("No autorizado.", show_alert=True)
        return
    p = obtener(int(q.data.split(":")[1]))
    if not p or p.estado != EN_REPARTO or p.repartidor_id != q.message.chat.id:
        await q.answer("Este pedido ya fue marcado.", show_alert=True)
        return
    actualizar(p.id, estado=CONFIRMANDO_ENTREGA)
    await q.answer()
    await q.edit_message_text(q.message.text_html + "\n\n📍 Esperando confirmación de entrega…", parse_mode=HTML)
    await q.message.reply_text(
        "Para marcar el pedido como entregado, primero envía la ubicación de dónde lo entregaste.",
        reply_markup=teclado_ubicacion_entrega(),
    )


async def en_mensaje_repartidor(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    p = pedido_en_confirmacion(update.effective_chat.id)
    if not p:
        return

    if p.entrega_lat is None:
        if not msg.location:
            await msg.reply_text(
                "Necesito la ubicación de la entrega. Toca el botón 📍 de abajo.",
                reply_markup=teclado_ubicacion_entrega(),
            )
            return
        actualizar(p.id, entrega_lat=msg.location.latitude, entrega_lon=msg.location.longitude)
        await msg.reply_text(
            "Ubicación recibida. Ahora escribe un texto confirmando la entrega "
            "(a quién se le entregó, alguna referencia, etc.).",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    if not msg.text:
        await msg.reply_text("Escribe un texto confirmando la entrega para terminar.")
        return

    p = actualizar(p.id, entrega_nota=msg.text.strip()[:500], estado=ENTREGADO)
    await msg.reply_text("✅ Entrega confirmada. ¡Gracias!")

    link = f"https://maps.google.com/?q={p.entrega_lat},{p.entrega_lon}"
    nota = html.escape(p.entrega_nota)
    await ctx.bot.send_message(
        p.user_id,
        f"✅ ¡Pedido entregado! Gracias por tu compra 🙌\n\n"
        f'<a href="{link}">Ver ubicación de la entrega</a>\n{nota}',
        parse_mode=HTML,
    )
    await ctx.bot.send_message(
        admin_chat_id(),
        f"✅ Pedido #{p.id} entregado.\n\n"
        f'<a href="{link}">Ver ubicación de la entrega</a>\n{nota}',
        parse_mode=HTML,
    )
