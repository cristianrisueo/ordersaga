# Tests de la lógica de pedidos: creación con su evento, y confirmación y cancelación idempotentes.
from conftest import make_event, outbox_events
from sqlalchemy.ext.asyncio import AsyncSession

from app import service
from app.schemas import OrderIn

# Datos del pedido que crean los tests
ORDER_IN = OrderIn(product_id="teclado", quantity=2, amount=50)


async def test_create_order_guarda_pedido_en_pending(session: AsyncSession) -> None:
    """Un pedido nuevo queda guardado en pending."""

    # Crea el pedido
    order = await service.create_order(session, ORDER_IN)

    # Lo relee de la base de datos y comprueba su estado
    await session.refresh(order)
    assert order.status == "pending"


async def test_create_order_escribe_order_created_con_datos_del_pedido(session: AsyncSession) -> None:
    """Crear un pedido escribe en el outbox order.created con el order_id y los datos del pedido."""

    # Crea el pedido
    order = await service.create_order(session, ORDER_IN)

    # Comprueba que el outbox tiene un único evento con los datos del pedido
    events = await outbox_events(session)
    assert [(event.event_type, event.payload) for event in events] == [
        (
            "order.created",
            {"event_type": "order.created", "order_id": str(order.id), "product_id": "teclado", "quantity": 2, "amount": 50},
        )
    ]


async def test_confirm_order_pasa_pending_a_confirmed(session: AsyncSession) -> None:
    """Confirmar un pedido en pending lo deja en confirmed."""

    # Prepara un pedido en pending
    order = await service.create_order(session, ORDER_IN)

    # Lo confirma
    await service.confirm_order(session, make_event("payment.completed", order.id))

    # Comprueba que ha quedado en confirmed
    await session.refresh(order)
    assert order.status == "confirmed"


async def test_confirm_order_no_cambia_pedido_cancelled(session: AsyncSession) -> None:
    """Confirmar un pedido ya cancelado no lo cambia."""

    # Prepara un pedido cancelado
    order = await service.create_order(session, ORDER_IN)
    await service.cancel_order(session, make_event("stock.failed", order.id))

    # Intenta confirmarlo
    await service.confirm_order(session, make_event("payment.completed", order.id))

    # Comprueba que sigue cancelado
    await session.refresh(order)
    assert order.status == "cancelled"


async def test_confirm_order_repetido_no_cambia_nada(session: AsyncSession) -> None:
    """Confirmar dos veces el mismo pedido lo deja en confirmed, sin errores."""

    # Prepara un pedido en pending
    order = await service.create_order(session, ORDER_IN)

    # Lo confirma dos veces, como si el evento llegara repetido
    event = make_event("payment.completed", order.id)
    await service.confirm_order(session, event)
    await service.confirm_order(session, event)

    # Comprueba que sigue en confirmed
    await session.refresh(order)
    assert order.status == "confirmed"


async def test_cancel_order_pasa_pending_a_cancelled(session: AsyncSession) -> None:
    """Cancelar un pedido en pending lo deja en cancelled."""

    # Prepara un pedido en pending
    order = await service.create_order(session, ORDER_IN)

    # Lo cancela
    await service.cancel_order(session, make_event("stock.failed", order.id))

    # Comprueba que ha quedado en cancelled
    await session.refresh(order)
    assert order.status == "cancelled"


async def test_cancel_order_no_cambia_pedido_confirmed(session: AsyncSession) -> None:
    """Cancelar un pedido ya confirmado no lo cambia."""

    # Prepara un pedido confirmado
    order = await service.create_order(session, ORDER_IN)
    await service.confirm_order(session, make_event("payment.completed", order.id))

    # Intenta cancelarlo
    await service.cancel_order(session, make_event("stock.released", order.id))

    # Comprueba que sigue confirmado
    await session.refresh(order)
    assert order.status == "confirmed"


async def test_confirm_order_no_escribe_en_outbox(session: AsyncSession) -> None:
    """Confirmar un pedido no añade eventos al outbox."""

    # Prepara un pedido en pending y lo confirma
    order = await service.create_order(session, ORDER_IN)
    await service.confirm_order(session, make_event("payment.completed", order.id))

    # Comprueba que en el outbox solo está el order.created de la creación
    events = await outbox_events(session)
    assert [event.event_type for event in events] == ["order.created"]


async def test_cancel_order_no_escribe_en_outbox(session: AsyncSession) -> None:
    """Cancelar un pedido no añade eventos al outbox."""

    # Prepara un pedido en pending y lo cancela
    order = await service.create_order(session, ORDER_IN)
    await service.cancel_order(session, make_event("stock.failed", order.id))

    # Comprueba que en el outbox solo está el order.created de la creación
    events = await outbox_events(session)
    assert [event.event_type for event in events] == ["order.created"]
