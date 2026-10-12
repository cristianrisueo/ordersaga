# Lógica de pagos: leer el pago de un pedido y cobrar o rechazar un pedido junto a su evento en la outbox.
import uuid

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import OutboxEvent, Payment
from app.schemas import OrderEvent


async def get_payment(session: AsyncSession, order_id: uuid.UUID) -> Payment | None:
    """Devuelve el pago del pedido, o None si no existe."""

    return await session.get(Payment, order_id)


async def charge_payment(session: AsyncSession, event: OrderEvent) -> None:
    """Cobra el pedido, o lo rechaza si supera el importe máximo, y escribe su evento en la outbox en una transacción."""

    # El pago se completa si el importe no supera el máximo y se rechaza si lo supera
    status = "completed" if event.amount <= get_settings().max_amount else "failed"

    async with session.begin():
        # Inserta el pago; si ya existía, el evento es repetido y no se hace nada más
        insert_payment = (
            insert(Payment)
            .values(order_id=event.order_id, amount=event.amount, status=status)
            .on_conflict_do_nothing(index_elements=[Payment.order_id])
            .returning(Payment.order_id)
        )
        if await session.scalar(insert_payment) is None:
            return

        # Escribe en la outbox payment.completed o payment.failed con los mismos campos del evento recibido
        payment_event = event.model_copy(update={"event_type": f"payment.{status}"})
        session.add(OutboxEvent(event_type=payment_event.event_type, payload=payment_event.model_dump(mode="json")))
