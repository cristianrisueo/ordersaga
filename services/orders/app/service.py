# Lógica de pedidos: crear uno junto a su evento en la outbox y leer uno por id.
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, OutboxEvent
from app.schemas import OrderEvent, OrderIn


async def create_order(session: AsyncSession, data: OrderIn) -> Order:
    """Guarda el pedido en pending y su evento order.created en la outbox, en la misma transacción."""

    # Crea el pedido
    order = Order(
        id=uuid.uuid7(),
        product_id=data.product_id,
        quantity=data.quantity,
        amount=data.amount,
        status="pending",
    )

    # Crea el evento del pedido
    event = OrderEvent(
        event_type="order.created",
        order_id=order.id,
        product_id=order.product_id,
        quantity=order.quantity,
        amount=order.amount,
    )

    # Guarda en una Tx pedido y evento en sus respectivas tablas (orders y outbox)
    async with session.begin():
        session.add(order)
        session.add(OutboxEvent(event_type=event.event_type, payload=event.model_dump(mode="json")))

    # Devuelve el pedido creado
    return order


async def get_order(session: AsyncSession, order_id: uuid.UUID) -> Order | None:
    """Devuelve el pedido, o None si no existe."""

    return await session.get(Order, order_id)
