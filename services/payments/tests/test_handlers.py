# Tests del reparto de eventos de payments: stock.reserved cobra y el resto de eventos de stock se ignoran.
from conftest import make_event, outbox_events
from sqlalchemy.ext.asyncio import AsyncSession

from app.events_handlers import handle_event
from app.models import Payment


async def test_stock_reserved_cobra(session: AsyncSession) -> None:
    """stock.reserved cobra el pedido."""

    # Llega la reserva de stock, tal y como sale de Kafka
    event = make_event("stock.reserved")
    await handle_event(session, event.model_dump(mode="json"))

    # Comprueba que el pago está completado
    payment = await session.get(Payment, event.order_id)
    assert payment is not None
    assert payment.status == "completed"


async def test_stock_failed_no_hace_nada(session: AsyncSession) -> None:
    """stock.failed se ignora: no hay pago ni eventos."""

    # Llega el fallo de stock, tal y como sale de Kafka
    event = make_event("stock.failed")
    await handle_event(session, event.model_dump(mode="json"))

    # Comprueba que no hay pago ni eventos en el outbox
    payment = await session.get(Payment, event.order_id)
    events = await outbox_events(session)
    assert payment is None
    assert events == []


async def test_stock_released_no_hace_nada(session: AsyncSession) -> None:
    """stock.released se ignora: no hay pago ni eventos."""

    # Llega la liberación de stock, tal y como sale de Kafka
    event = make_event("stock.released")
    await handle_event(session, event.model_dump(mode="json"))

    # Comprueba que no hay pago ni eventos en el outbox
    payment = await session.get(Payment, event.order_id)
    events = await outbox_events(session)
    assert payment is None
    assert events == []
