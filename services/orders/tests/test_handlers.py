# Tests del reparto de eventos de orders: qué eventos confirman, cuáles cancelan y cuáles se ignoran.
from conftest import make_event
from sqlalchemy.ext.asyncio import AsyncSession

from app import service
from app.events_handlers import handle_event
from app.schemas import OrderIn

# Datos del pedido que crean los tests
ORDER_IN = OrderIn(product_id="teclado", quantity=2, amount=50)


async def test_payment_completed_confirma_pedido(session: AsyncSession) -> None:
    """payment.completed confirma el pedido."""

    # Prepara un pedido en pending
    order = await service.create_order(session, ORDER_IN)

    # Llega el evento, tal y como sale de Kafka
    await handle_event(session, make_event("payment.completed", order.id).model_dump(mode="json"))

    # Comprueba que el pedido está confirmado
    await session.refresh(order)
    assert order.status == "confirmed"


async def test_stock_failed_cancela_pedido(session: AsyncSession) -> None:
    """stock.failed cancela el pedido."""

    # Prepara un pedido en pending
    order = await service.create_order(session, ORDER_IN)

    # Llega el evento, tal y como sale de Kafka
    await handle_event(session, make_event("stock.failed", order.id).model_dump(mode="json"))

    # Comprueba que el pedido está cancelado
    await session.refresh(order)
    assert order.status == "cancelled"


async def test_stock_released_cancela_pedido(session: AsyncSession) -> None:
    """stock.released cancela el pedido."""

    # Prepara un pedido en pending
    order = await service.create_order(session, ORDER_IN)

    # Llega el evento, tal y como sale de Kafka
    await handle_event(session, make_event("stock.released", order.id).model_dump(mode="json"))

    # Comprueba que el pedido está cancelado
    await session.refresh(order)
    assert order.status == "cancelled"


async def test_payment_failed_no_toca_pedido(session: AsyncSession) -> None:
    """payment.failed se ignora: orders espera a que stock libere las unidades."""

    # Prepara un pedido en pending
    order = await service.create_order(session, ORDER_IN)

    # Llega el evento, tal y como sale de Kafka
    await handle_event(session, make_event("payment.failed", order.id).model_dump(mode="json"))

    # Comprueba que el pedido sigue en pending
    await session.refresh(order)
    assert order.status == "pending"


async def test_stock_reserved_no_toca_pedido(session: AsyncSession) -> None:
    """stock.reserved se ignora: orders espera al resultado del pago."""

    # Prepara un pedido en pending
    order = await service.create_order(session, ORDER_IN)

    # Llega el evento, tal y como sale de Kafka
    await handle_event(session, make_event("stock.reserved", order.id).model_dump(mode="json"))

    # Comprueba que el pedido sigue en pending
    await session.refresh(order)
    assert order.status == "pending"
