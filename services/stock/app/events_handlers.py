# Manejadores de eventos: deciden qué hacer con cada mensaje que llega de Kafka.
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app import service
from app.schemas import OrderEvent

logger = logging.getLogger("app.events_handlers")


async def handle_event(session: AsyncSession, value: dict[str, Any]) -> None:
    """Valida el mensaje; reserva stock si es order.created y lo libera si es payment.failed; el resto se ignora."""

    # Valida el mensaje; si no es un evento válido, la excepción tumba el consumidor
    event = OrderEvent.model_validate(value)

    # Reacciona a los pedidos creados y a los pagos rechazados (compensación)
    if event.event_type == "order.created":
        await service.reserve_stock(session, event)
    elif event.event_type == "payment.failed":
        await service.release_stock(session, event)
    else:
        logger.debug("Ignorado %s del pedido %s", event.event_type, event.order_id)
