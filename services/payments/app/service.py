# Lógica de pagos: leer el pago de un pedido y cobrar un pedido junto a su evento en la outbox.
import uuid

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OutboxEvent, Payment
from app.schemas import OrderEvent


async def get_payment(session: AsyncSession, order_id: uuid.UUID) -> Payment | None:
    """Devuelve el pago del pedido, o None si no existe."""

    return await session.get(Payment, order_id)


async def charge_payment(session: AsyncSession, event: OrderEvent) -> None:
    """Cobra el pedido y escribe payment.completed en la outbox, todo en la misma transacción."""

    async with session.begin():
        # Inserta el pago; si ya existía, el evento es repetido y no se hace nada más
        insert_payment = (
            insert(Payment)
            .values(order_id=event.order_id, amount=event.amount, status="completed")
            .on_conflict_do_nothing(index_elements=[Payment.order_id])
            .returning(Payment.order_id)
        )
        if await session.scalar(insert_payment) is None:
            return

        # Escribe en la outbox payment.completed con los mismos campos del evento recibido
        completed_event = event.model_copy(update={"event_type": "payment.completed"})
        session.add(OutboxEvent(event_type=completed_event.event_type, payload=completed_event.model_dump(mode="json")))
