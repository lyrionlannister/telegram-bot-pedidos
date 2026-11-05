"""Estados del pedido."""
CARRITO = "carrito"
ESPERA_PAGO = "espera_pago"
REVISION_PAGO = "revision_pago"
PIDE_UBICACION = "pide_ubicacion"
PREPARANDO = "preparando"
EN_REPARTO = "en_reparto"
CONFIRMANDO_ENTREGA = "confirmando_entrega"
ENTREGADO = "entregado"
CANCELADO = "cancelado"

CERRADOS = (ENTREGADO, CANCELADO)
CANCELABLES = (CARRITO, ESPERA_PAGO)
