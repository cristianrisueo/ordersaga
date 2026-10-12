# Tests del reparto de eventos de stock: qué eventos reservan, cuáles liberan y cuáles se ignoran.
from conftest import make_event, outbox_events
from sqlalchemy.ext.asyncio import AsyncSession

from app.events_handlers import handle_event
from app.models import Product


async def test_order_created_reserva(session: AsyncSession) -> None:
    """order.created reserva las unidades del pedido."""

    # Llega el pedido creado, tal y como sale de Kafka
    await handle_event(session, make_event("order.created").model_dump(mode="json"))

    # Comprueba que se han descontado 2 teclados
    product = await session.get(Product, "teclado")
    assert product is not None
    assert product.available == 3


async def test_payment_failed_libera(session: AsyncSession) -> None:
    """payment.failed libera las unidades reservadas del pedido."""

    # Prepara una reserva de 2 teclados (quedan 3)
    event = make_event("order.created")
    await handle_event(session, event.model_dump(mode="json"))

    # Llega el pago rechazado del mismo pedido
    await handle_event(session, {**event.model_dump(mode="json"), "event_type": "payment.failed"})

    # Comprueba que vuelve a haber 5
    product = await session.get(Product, "teclado")
    assert product is not None
    assert product.available == 5


async def test_payment_completed_no_hace_nada(session: AsyncSession) -> None:
    """payment.completed se ignora: la reserva se mantiene y no se escriben eventos."""

    # Prepara una reserva de 2 teclados (quedan 3)
    event = make_event("order.created")
    await handle_event(session, event.model_dump(mode="json"))

    # Llega el pago completado del mismo pedido
    await handle_event(session, {**event.model_dump(mode="json"), "event_type": "payment.completed"})

    # Comprueba que siguen quedando 3 y que en el outbox solo está el stock.reserved de la reserva
    product = await session.get(Product, "teclado")
    events = await outbox_events(session)
    assert product is not None
    assert product.available == 3
    assert [row.event_type for row in events] == ["stock.reserved"]
