# Manejadores de eventos: deciden qué hacer con cada mensaje que llega de Kafka.
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app import service
from app.schemas import OrderEvent

logger = logging.getLogger("app.events_handlers")


async def handle_event(session: AsyncSession, value: dict[str, Any]) -> None:
    """Valida el mensaje y cobra el pedido si es stock.reserved; el resto de tipos se ignoran."""

    # Valida el mensaje; si no es un evento válido, la excepción tumba el consumidor
    event = OrderEvent.model_validate(value)

    # Reacciona solo a las reservas de stock
    if event.event_type == "stock.reserved":
        await service.charge_payment(session, event)
    else:
        logger.debug("Ignorado %s del pedido %s", event.event_type, event.order_id)
