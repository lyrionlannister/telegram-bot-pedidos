"""Acceso a datos: tabla pedidos vía SQLAlchemy ORM."""
from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from .config import config
from .constants import CARRITO, CERRADOS, CONFIRMANDO_ENTREGA
from .models import Base, Pedido

engine = create_engine(f"sqlite:///{config.rutas.db_path}")


def init_db() -> None:
    Base.metadata.create_all(engine)
    # create_all no agrega columnas a una tabla ya existente, así que migramos a mano.
    with engine.begin() as conn:
        existentes = {fila[1] for fila in conn.exec_driver_sql("PRAGMA table_info(pedidos)")}
        for columna, tipo in (
            ("entrega_lat", "DOUBLE"),
            ("entrega_lon", "DOUBLE"),
            ("entrega_nota", "VARCHAR"),
            ("repartidor_id", "INTEGER"),
        ):
            if columna not in existentes:
                conn.exec_driver_sql(f"ALTER TABLE pedidos ADD COLUMN {columna} {tipo}")


def crear_pedido(user) -> Pedido:
    with Session(engine) as session:
        pedido = Pedido(
            user_id=user.id,
            username=user.username,
            estado=CARRITO,
            creado=datetime.now().isoformat(timespec="seconds"),
        )
        session.add(pedido)
        session.commit()
        session.refresh(pedido)
        session.expunge(pedido)
        return pedido


def obtener(pedido_id: int) -> Pedido | None:
    with Session(engine) as session:
        pedido = session.get(Pedido, pedido_id)
        if pedido:
            session.expunge(pedido)
        return pedido


def pedido_activo(user_id: int) -> Pedido | None:
    with Session(engine) as session:
        pedido = session.scalars(
            select(Pedido)
            .where(Pedido.user_id == user_id, Pedido.estado.not_in(CERRADOS))
            .order_by(Pedido.id.desc())
            .limit(1)
        ).first()
        if pedido:
            session.expunge(pedido)
        return pedido


def pedido_en_confirmacion(repartidor_id: int) -> Pedido | None:
    with Session(engine) as session:
        pedido = session.scalars(
            select(Pedido)
            .where(Pedido.estado == CONFIRMANDO_ENTREGA, Pedido.repartidor_id == repartidor_id)
            .order_by(Pedido.id.desc())
            .limit(1)
        ).first()
        if pedido:
            session.expunge(pedido)
        return pedido


def actualizar(pedido_id: int, **campos) -> Pedido | None:
    with Session(engine) as session:
        pedido = session.get(Pedido, pedido_id)
        for campo, valor in campos.items():
            setattr(pedido, campo, valor)
        session.commit()
        session.refresh(pedido)
        session.expunge(pedido)
        return pedido
