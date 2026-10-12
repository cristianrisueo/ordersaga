# Tests de la lógica de stock: reservas con y sin unidades, liberación de reservas e idempotencia de ambas.
from conftest import make_event, outbox_events
from sqlalchemy.ext.asyncio import AsyncSession

from app import service
from app.models import Product, Reservation


async def test_reserve_stock_con_unidades_descuenta(session: AsyncSession) -> None:
    """Reservar 2 teclados de 5 deja 3 disponibles."""

    # Reserva 2 teclados
    await service.reserve_stock(session, make_event("order.created"))

    # Comprueba las unidades que quedan
    product = await session.get(Product, "teclado")
    assert product is not None
    assert product.available == 3


async def test_reserve_stock_con_unidades_marca_reserved(session: AsyncSession) -> None:
    """Con unidades suficientes, la reserva queda en reserved."""

    # Reserva 2 teclados
    event = make_event("order.created")
    await service.reserve_stock(session, event)

    # Comprueba el estado de la reserva
    reservation = await session.get(Reservation, event.order_id)
    assert reservation is not None
    assert reservation.status == "reserved"


async def test_reserve_stock_con_unidades_escribe_stock_reserved(session: AsyncSession) -> None:
    """Con unidades suficientes, el outbox tiene stock.reserved con los datos del evento recibido."""

    # Reserva 2 teclados
    event = make_event("order.created")
    await service.reserve_stock(session, event)

    # Comprueba que el outbox tiene un único stock.reserved con los mismos campos del evento
    events = await outbox_events(session)
    assert [(row.event_type, row.payload) for row in events] == [
        ("stock.reserved", {**event.model_dump(mode="json"), "event_type": "stock.reserved"})
    ]


async def test_reserve_stock_sin_unidades_no_descuenta(session: AsyncSession) -> None:
    """Pedir 5 monitores cuando solo hay 1 no descuenta nada."""

    # Intenta reservar 5 monitores
    await service.reserve_stock(session, make_event("order.created", product_id="monitor", quantity=5))

    # Comprueba que sigue habiendo 1
    product = await session.get(Product, "monitor")
    assert product is not None
    assert product.available == 1


async def test_reserve_stock_sin_unidades_marca_failed(session: AsyncSession) -> None:
    """Sin unidades suficientes, la reserva queda en failed."""

    # Intenta reservar 5 monitores
    event = make_event("order.created", product_id="monitor", quantity=5)
    await service.reserve_stock(session, event)

    # Comprueba el estado de la reserva
    reservation = await session.get(Reservation, event.order_id)
    assert reservation is not None
    assert reservation.status == "failed"


async def test_reserve_stock_sin_unidades_escribe_stock_failed(session: AsyncSession) -> None:
    """Sin unidades suficientes, el outbox tiene stock.failed."""

    # Intenta reservar 5 monitores
    await service.reserve_stock(session, make_event("order.created", product_id="monitor", quantity=5))

    # Comprueba que el outbox tiene un único stock.failed
    events = await outbox_events(session)
    assert [row.event_type for row in events] == ["stock.failed"]


async def test_reserve_stock_producto_inexistente_marca_failed(session: AsyncSession) -> None:
    """Un producto que no está en el catálogo deja la reserva en failed."""

    # Intenta reservar un producto que no existe
    event = make_event("order.created", product_id="raton")
    await service.reserve_stock(session, event)

    # Comprueba el estado de la reserva
    reservation = await session.get(Reservation, event.order_id)
    assert reservation is not None
    assert reservation.status == "failed"


async def test_reserve_stock_producto_inexistente_escribe_stock_failed(session: AsyncSession) -> None:
    """Un producto que no está en el catálogo escribe stock.failed en el outbox."""

    # Intenta reservar un producto que no existe
    await service.reserve_stock(session, make_event("order.created", product_id="raton"))

    # Comprueba que el outbox tiene un único stock.failed
    events = await outbox_events(session)
    assert [row.event_type for row in events] == ["stock.failed"]


async def test_reserve_stock_repetido_descuenta_una_vez(session: AsyncSession) -> None:
    """El mismo order.created dos veces descuenta las unidades una sola vez."""

    # Reserva dos veces con el mismo evento, como si llegara repetido
    event = make_event("order.created")
    await service.reserve_stock(session, event)
    await service.reserve_stock(session, event)

    # Comprueba que solo se han descontado 2 unidades
    product = await session.get(Product, "teclado")
    assert product is not None
    assert product.available == 3


async def test_reserve_stock_repetido_escribe_un_solo_evento(session: AsyncSession) -> None:
    """El mismo order.created dos veces escribe un solo stock.reserved."""

    # Reserva dos veces con el mismo evento, como si llegara repetido
    event = make_event("order.created")
    await service.reserve_stock(session, event)
    await service.reserve_stock(session, event)

    # Comprueba que el outbox tiene un único evento
    events = await outbox_events(session)
    assert [row.event_type for row in events] == ["stock.reserved"]


async def test_release_stock_marca_released(session: AsyncSession) -> None:
    """Liberar una reserva en reserved la deja en released."""

    # Prepara una reserva de 2 teclados
    event = make_event("order.created")
    await service.reserve_stock(session, event)

    # Llega el pago rechazado y se libera
    await service.release_stock(session, event.model_copy(update={"event_type": "payment.failed"}))

    # Comprueba el estado de la reserva
    reservation = await session.get(Reservation, event.order_id)
    assert reservation is not None
    assert reservation.status == "released"


async def test_release_stock_devuelve_unidades(session: AsyncSession) -> None:
    """Liberar una reserva de 2 teclados devuelve las 2 unidades."""

    # Prepara una reserva de 2 teclados (quedan 3)
    event = make_event("order.created")
    await service.reserve_stock(session, event)

    # Llega el pago rechazado y se libera
    await service.release_stock(session, event.model_copy(update={"event_type": "payment.failed"}))

    # Comprueba que vuelve a haber 5
    product = await session.get(Product, "teclado")
    assert product is not None
    assert product.available == 5


async def test_release_stock_escribe_stock_released(session: AsyncSession) -> None:
    """Liberar una reserva escribe stock.released en el outbox con los datos del evento recibido."""

    # Prepara una reserva de 2 teclados
    event = make_event("order.created")
    await service.reserve_stock(session, event)

    # Llega el pago rechazado y se libera
    failed_event = event.model_copy(update={"event_type": "payment.failed"})
    await service.release_stock(session, failed_event)

    # Comprueba que tras el stock.reserved de la reserva viene stock.released con los mismos campos
    events = await outbox_events(session)
    assert [(row.event_type, row.payload) for row in events][1:] == [
        ("stock.released", {**failed_event.model_dump(mode="json"), "event_type": "stock.released"})
    ]


async def test_release_stock_repetido_devuelve_unidades_una_vez(session: AsyncSession) -> None:
    """El mismo payment.failed dos veces devuelve las unidades una sola vez."""

    # Prepara una reserva de 2 teclados (quedan 3)
    event = make_event("order.created")
    await service.reserve_stock(session, event)

    # Libera dos veces con el mismo evento, como si llegara repetido
    failed_event = event.model_copy(update={"event_type": "payment.failed"})
    await service.release_stock(session, failed_event)
    await service.release_stock(session, failed_event)

    # Comprueba que hay 5, no 7
    product = await session.get(Product, "teclado")
    assert product is not None
    assert product.available == 5


async def test_release_stock_repetido_escribe_un_solo_evento(session: AsyncSession) -> None:
    """El mismo payment.failed dos veces escribe un solo stock.released."""

    # Prepara una reserva de 2 teclados
    event = make_event("order.created")
    await service.reserve_stock(session, event)

    # Libera dos veces con el mismo evento, como si llegara repetido
    failed_event = event.model_copy(update={"event_type": "payment.failed"})
    await service.release_stock(session, failed_event)
    await service.release_stock(session, failed_event)

    # Comprueba que el outbox tiene la reserva y una sola liberación
    events = await outbox_events(session)
    assert [row.event_type for row in events] == ["stock.reserved", "stock.released"]


async def test_release_stock_sobre_reserva_failed_no_hace_nada(session: AsyncSession) -> None:
    """Liberar una reserva que quedó en failed no devuelve unidades ni escribe eventos."""

    # Prepara una reserva fallida de 5 monitores
    event = make_event("order.created", product_id="monitor", quantity=5)
    await service.reserve_stock(session, event)

    # Intenta liberarla
    await service.release_stock(session, event.model_copy(update={"event_type": "payment.failed"}))

    # Comprueba que el monitor sigue en 1 y que en el outbox solo está el stock.failed de la reserva
    product = await session.get(Product, "monitor")
    events = await outbox_events(session)
    assert product is not None
    assert product.available == 1
    assert [row.event_type for row in events] == ["stock.failed"]


async def test_release_stock_sin_reserva_no_hace_nada(session: AsyncSession) -> None:
    """Liberar un pedido sin reserva no devuelve unidades ni escribe eventos."""

    # Intenta liberar un pedido que nunca se reservó
    await service.release_stock(session, make_event("payment.failed"))

    # Comprueba que el teclado sigue en 5 y que el outbox está vacío
    product = await session.get(Product, "teclado")
    events = await outbox_events(session)
    assert product is not None
    assert product.available == 5
    assert events == []


async def test_release_stock_devuelve_unidades_de_la_reserva(session: AsyncSession) -> None:
    """Se devuelven las unidades guardadas en la reserva aunque el evento traiga otra quantity."""

    # Prepara una reserva de 2 teclados (quedan 3)
    event = make_event("order.created")
    await service.reserve_stock(session, event)

    # Llega un pago rechazado con otra quantity
    await service.release_stock(session, event.model_copy(update={"event_type": "payment.failed", "quantity": 4}))

    # Comprueba que se han devuelto 2 (hay 5) y no 4 (habría 7)
    product = await session.get(Product, "teclado")
    assert product is not None
    assert product.available == 5
