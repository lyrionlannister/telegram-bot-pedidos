"""Modelo ORM de la tabla pedidos."""
from sqlalchemy import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .constants import CARRITO


class Base(DeclarativeBase):
    pass


class Pedido(Base):
    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(nullable=False)
    username: Mapped[str | None] = mapped_column(default=None)
    estado: Mapped[str] = mapped_column(nullable=False, default=CARRITO)
    items: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    nombre: Mapped[str | None] = mapped_column(default=None)
    telefono: Mapped[str | None] = mapped_column(default=None)
    lat: Mapped[float | None] = mapped_column(default=None)
    lon: Mapped[float | None] = mapped_column(default=None)
    comprobante: Mapped[str | None] = mapped_column(default=None)
    repartidor_id: Mapped[int | None] = mapped_column(default=None)
    entrega_lat: Mapped[float | None] = mapped_column(default=None)
    entrega_lon: Mapped[float | None] = mapped_column(default=None)
    entrega_nota: Mapped[str | None] = mapped_column(default=None)
    creado: Mapped[str] = mapped_column(nullable=False)
