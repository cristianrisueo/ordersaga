# Lógica de pedidos: crear uno junto a su evento en la outbox y leer uno por id.
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, OutboxEvent
from app.schemas import OrderEvent, OrderIn


async def create_order(session: AsyncSession, data: OrderIn) -> Order:
    """Guarda el pedido en pending y su evento order.created en la outbox, en la misma transacción."""

    # El id se genera aquí para poder meterlo en el evento antes de escribir en la base de datos
    order = Order(
        id=uuid.uuid7(),
        product_id=data.product_id,
        quantity=data.quantity,
        amount=data.amount,
        status="pending",
    )

    # El payload es exactamente el mensaje que publicará el productor
    event = OrderEvent(
        event_type="order.created",
        order_id=order.id,
        product_id=order.product_id,
        quantity=order.quantity,
        amount=order.amount,
    )

    # Pedido y evento se confirman juntos: o se guardan los dos o ninguno
    async with session.begin():
        session.add(order)
        session.add(OutboxEvent(event_type=event.event_type, payload=event.model_dump(mode="json")))

    return order


async def get_order(session: AsyncSession, order_id: uuid.UUID) -> Order | None:
    """Devuelve el pedido, o None si no existe."""

    return await session.get(Order, order_id)
