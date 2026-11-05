# Bot de pedidos para Telegram

## Puesta en marcha

1. **Crea el bot:** en Telegram abre @BotFather → `/newbot` → copia el token.
2. **Instala [uv](https://docs.astral.sh/uv/)** y luego, en esta carpeta:
   ```bash
   uv sync
   ```
3. **Configura:** copia `.env.example` como `.env` y pon tu token.
4. **Obtén los IDs:** corre el bot (`uv run python src/main.py`). Desde la cuenta del admin y
   desde la del repartidor, mándale cualquier mensaje al bot y revisa la consola: cada mensaje
   que llega se loguea como `<- update de <ID>`. Crea `equipo.json` a mano con esos números:
   ```json
   {"admin_chat_id": 111111111, "repartidores": [{"chat_id": 222222222, "nombre": "Repartidor", "activo": true}]}
   ```
   y reinicia.
5. **Edita el catálogo** desde el chat del admin con `/catalogo`, o directo en `catalogo.json`.
6. Corre `uv run python src/main.py`.

## Flujo

| Paso | Quién | Qué pasa |
|---|---|---|
| 0–1 | Cliente | `/start` → "Hacer pedido" → ve el catálogo con botones (bloqueado si el bot está desactivado) |
| 1 | Cliente | Agrega productos, toca "Terminar pedido" |
| 2 | Bot | Muestra el resumen y los datos de pago |
| 3 | Cliente | Envía foto o documento del comprobante (puede cancelar con el botón ❌) |
| 4 | Admin | Recibe el comprobante con botones ✅ Confirmar / ❌ Rechazar |
| 5 | Cliente | Comparte su ubicación con el botón 📍 |
| 6 | Admin | Recibe ubicación + pedido con botón "📦 Paquete listo" |
| 7 | Bot | Al tocarlo, asigna al repartidor disponible al frente de la cola y le manda la ubicación + el pedido con botón "✅ Entregado" |
| 8 | Repartidor | Toca "✅ Entregado", manda la ubicación de la entrega y un texto confirmándola (ambos obligatorios) |
| 9 | Bot | Marca el pedido como entregado y avisa al cliente y al admin con la ubicación y la nota de la entrega |

El cliente puede cancelar (botón o `/cancelar`) mientras su pedido no haya sido enviado a revisión de pago.

## Comandos

**Cliente**
- `/start` — ver el catálogo y empezar un pedido
- `/cancelar` — cancelar el pedido activo (si aún se puede)

**Admin** (solo responde al `admin_chat_id` configurado en `equipo.json`)
- `/catalogo` — ver o reemplazar el catálogo completo (pegando el JSON)
- `/pago` — ver o cambiar los datos de pago (banco, CLABE, tarjeta, etc. en JSON)
- `/equipo` — ver o cambiar el admin y la cola de repartidores (JSON)
- `/activar` / `/desactivar` — abre o cierra el bot a pedidos nuevos (con botón para alternar)

**Repartidor** (debe estar dado de alta en `/equipo`)
- `/conectar` / `/desconectar` — entra o sale de la cola de entregas (con botón para alternar)

## Notas

- Los pedidos se guardan en `pedidos.db` (SQLite vía SQLAlchemy). Las columnas nuevas se
  migran solas al arrancar el bot.
- `catalogo.json`, `datos_pago.json`, `equipo.json` y `apertura.json` se editan en caliente
  desde los comandos del admin (no requieren reiniciar el bot) y no se suben a git.
- La cola de repartidores es por turnos: al asignar una entrega se toma el primero activo
  de la lista y se manda al final, así se reparte el trabajo entre todos.
- El botón de ubicación funciona en el celular. En la versión de escritorio el cliente
  puede usar 📎 → Ubicación.
- Cada update entrante y cada llamada saliente a la API de Telegram quedan en el log de
  consola con el chat id correspondiente.
- Para tenerlo 24/7, súbelo a un VPS o a un servicio como Railway o Render y deja
  corriendo `uv run python src/main.py`.
