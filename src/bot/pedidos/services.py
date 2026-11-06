"""Lógica de presentación: textos, totales y teclados."""
import html

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from .catalogo import CATALOGO, PRODUCTOS
from .models import Pedido


def total(items: dict) -> float:
    return sum(PRODUCTOS[pid]["precio"] * q for pid, q in items.items() if pid in PRODUCTOS)


def resumen(p: Pedido, para_admin: bool = False) -> str:
    items = p.items
    lineas = [f"<b>Pedido #{p.id}</b>"]
    for pid, q in items.items():
        prod = PRODUCTOS.get(pid)
        if prod:
            lineas.append(
                f"• {q} × {html.escape(prod['nombre'])} — ${prod['precio'] * q:,.2f}"
            )
    if not items:
        lineas.append("(aún no agregas productos)")
    lineas.append(f"<b>Total: ${total(items):,.2f}</b>")
    if p.nombre:
        lineas.append(f"\nNombre: {html.escape(p.nombre)}")
    if p.telefono:
        lineas.append(f"Teléfono: {html.escape(p.telefono)}")
    if para_admin and p.username:
        lineas.append(f"Usuario: @{html.escape(p.username)}")
    return "\n".join(lineas)


def texto_carrito(p: Pedido) -> str:
    return "🛍 <b>Catálogo</b>\nToca un producto para agregarlo a tu pedido.\n\n" + resumen(p)


def teclado_catalogo() -> InlineKeyboardMarkup:
    filas = [
        [InlineKeyboardButton(f"➕ {p['nombre']} (${p['precio']:,.0f})", callback_data=f"add:{p['id']}")]
        for p in CATALOGO
    ]
    filas.append(
        [
            InlineKeyboardButton("🗑 Vaciar", callback_data="vaciar"),
            InlineKeyboardButton("✅ Terminar pedido", callback_data="terminar"),
        ]
    )
    filas.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")])
    return InlineKeyboardMarkup(filas)


def teclado_ubicacion() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📍 Enviar mi ubicación", request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def link_mapa(p: Pedido) -> str:
    return f'<a href="https://maps.google.com/?q={p.lat},{p.lon}">Abrir en Google Maps</a>'
