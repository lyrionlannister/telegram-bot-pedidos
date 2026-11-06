"""Comandos y mensajes del cliente (catálogo, datos, pago, ubicación)."""
import html

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from ..apertura import MENSAJE_FUERA_DE_LINEA, esta_abierto, registrar_pendiente
from ..config import HTML, config
from ..equipo import admin_chat_id
from ..pagos import texto_datos_pago
from ..pedidos.catalogo import PRODUCTOS
from ..pedidos.constants import (
    CANCELABLES,
    CANCELADO,
    CARRITO,
    EN_REPARTO,
    ESPERA_PAGO,
    PIDE_UBICACION,
    PREPARANDO,
    REVISION_PAGO,
)
from ..pedidos.repository import actualizar, crear_pedido, pedido_activo
from ..pedidos.services import (
    link_mapa,
    resumen,
    teclado_catalogo,
    teclado_ubicacion,
    texto_carrito,
)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not esta_abierto() and not pedido_activo(update.effective_user.id):
        if update.effective_chat.id != admin_chat_id():
            registrar_pendiente(update.effective_chat.id)
        await update.effective_message.reply_text(MENSAJE_FUERA_DE_LINEA)
        return
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Hacer pedido", callback_data="nuevo")]])
    await update.effective_message.reply_text(
        f"¡Hola! 👋 Bienvenido a {config.negocio.nombre}.\nToca el botón para ver el catálogo y hacer tu pedido.",
        reply_markup=kb,
    )


async def cmd_cancelar(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    p = pedido_activo(update.effective_user.id)
    if not p:
        await update.message.reply_text("No tienes ningún pedido activo.")
    elif p.estado in CANCELABLES:
        actualizar(p.id, estado=CANCELADO)
        await update.message.reply_text(
            "Pedido cancelado. Escribe /start cuando quieras hacer otro.",
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        await update.message.reply_text(
            "Tu pedido ya está en proceso y no se puede cancelar desde aquí. "
            "Escríbenos directamente si necesitas un cambio."
        )


async def cb_cliente(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    data = q.data
    p = pedido_activo(q.from_user.id)

    if data == "nuevo":
        if p and p.estado != CARRITO:
            await q.answer(f"Ya tienes un pedido en curso (#{p.id}).", show_alert=True)
            return
        if not p and not esta_abierto():
            if q.message.chat.id != admin_chat_id():
                registrar_pendiente(q.message.chat.id)
            await q.answer(MENSAJE_FUERA_DE_LINEA, show_alert=True)
            return
        if not p:
            p = crear_pedido(q.from_user)
        await q.answer()
        await q.message.reply_text(texto_carrito(p), parse_mode=HTML, reply_markup=teclado_catalogo())
        return

    if data == "cancelar":
        if not p or p.estado not in CANCELABLES:
            await q.answer("Este pedido ya no se puede cancelar.", show_alert=True)
            return
        actualizar(p.id, estado=CANCELADO)
        await q.answer()
        await q.edit_message_text("Pedido cancelado. Escribe /start cuando quieras hacer otro.")
        return

    if not p or p.estado != CARRITO:
        await q.answer("Este carrito ya no está activo. Escribe /start.", show_alert=True)
        return

    items = p.items

    if data.startswith("add:"):
        prod_id = data[4:]
        if prod_id not in PRODUCTOS:
            await q.answer("Ese producto ya no está disponible.", show_alert=True)
            return
        items[prod_id] = items.get(prod_id, 0) + 1
        p = actualizar(p.id, items=items)
        await q.answer(f"Agregado: {PRODUCTOS[prod_id]['nombre']}")

    elif data == "vaciar":
        p = actualizar(p.id, items={})
        await q.answer("Carrito vacío")

    elif data == "terminar":
        if not items:
            await q.answer("Agrega al menos un producto.", show_alert=True)
            return
        p = actualizar(p.id, estado=ESPERA_PAGO)
        await q.answer()
        await q.edit_message_text(resumen(p), parse_mode=HTML)
        await q.message.reply_text(
            "💳 <b>Datos para pagar</b>\n"
            + html.escape(texto_datos_pago())
            + "\n\nCuando pagues, mándame aquí una <b>foto o captura del comprobante</b>.",
            parse_mode=HTML,
        )
        return

    try:
        await q.edit_message_text(texto_carrito(p), parse_mode=HTML, reply_markup=teclado_catalogo())
    except BadRequest:
        pass  # "message is not modified" (p. ej. vaciar un carrito ya vacío)


async def en_mensaje(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    p = pedido_activo(msg.from_user.id)
    if not p:
        await cmd_start(update, ctx)
        return

    estado = p.estado

    if estado == CARRITO:
        await msg.reply_text(
            "Usa los botones del catálogo para armar tu pedido 👇",
        )
        await msg.reply_text(texto_carrito(p), parse_mode=HTML, reply_markup=teclado_catalogo())

    elif estado == ESPERA_PAGO:
        if msg.photo:
            file_id, es_foto = msg.photo[-1].file_id, True
        elif msg.document:
            file_id, es_foto = msg.document.file_id, False
        else:
            await msg.reply_text(
                "Estoy esperando la foto o captura de tu comprobante de pago 🧾",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")]]
                ),
            )
            return
        p = actualizar(p.id, comprobante=file_id, estado=REVISION_PAGO)
        await msg.reply_text("¡Recibido! 🙌 Estamos verificando tu pago, te aviso en cuanto quede confirmado.")

        kb = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("✅ Confirmar pago", callback_data=f"pago_ok:{p.id}"),
                InlineKeyboardButton("❌ Rechazar", callback_data=f"pago_no:{p.id}"),
            ]]
        )
        caption = "🧾 <b>Comprobante recibido</b>\n\n" + resumen(p, para_admin=True)
        if es_foto:
            await ctx.bot.send_photo(admin_chat_id(), file_id, caption=caption, parse_mode=HTML, reply_markup=kb)
        else:
            await ctx.bot.send_document(admin_chat_id(), file_id, caption=caption, parse_mode=HTML, reply_markup=kb)

    elif estado == REVISION_PAGO:
        await msg.reply_text("Tu pago está en revisión ⏳ Te aviso en cuanto quede confirmado.")

    elif estado == PIDE_UBICACION:
        loc = msg.location
        if not loc:
            await msg.reply_text(
                "Necesito tu <b>ubicación</b> para la entrega. Toca el botón 📍 de abajo "
                "(o usa 📎 → Ubicación).",
                parse_mode=HTML,
                reply_markup=teclado_ubicacion(),
            )
            return
        p = actualizar(p.id, lat=loc.latitude, lon=loc.longitude, estado=PREPARANDO)
        await msg.reply_text(
            "📍 ¡Ubicación recibida! Estamos preparando tu pedido.",
            reply_markup=ReplyKeyboardRemove(),
        )
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("📦 Paquete listo", callback_data=f"listo:{p.id}")]]
        )
        await ctx.bot.send_location(admin_chat_id(), latitude=p.lat, longitude=p.lon)
        await ctx.bot.send_message(
            admin_chat_id(),
            "📦 <b>Preparar paquete</b>\n\n" + resumen(p, para_admin=True) + "\n" + link_mapa(p),
            parse_mode=HTML,
            reply_markup=kb,
        )

    elif estado == PREPARANDO:
        await msg.reply_text("Estamos preparando tu pedido 📦 Te aviso cuando salga.")

    elif estado == EN_REPARTO:
        await msg.reply_text("Tu pedido ya va en camino 🛵")
