# Tests de la lógica de pagos: cobro hasta el importe máximo, rechazo por encima e idempotencia.
from conftest import make_event, outbox_events
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import service
from app.config import get_settings
from app.models import Payment

# Importe máximo que se cobra, el mismo que usa el service
MAX_AMOUNT = get_settings().max_amount


async def test_charge_payment_bajo_el_maximo_completa(session: AsyncSession) -> None:
    """Un importe por debajo del máximo deja el pago en completed."""

    # Cobra 50 euros
    event = make_event("stock.reserved")
    await service.charge_payment(session, event)

    # Comprueba el estado del pago
    payment = await session.get(Payment, event.order_id)
    assert payment is not None
    assert payment.status == "completed"


async def test_charge_payment_en_el_maximo_completa(session: AsyncSession) -> None:
    """Un importe exactamente igual al máximo todavía se cobra."""

    # Cobra justo el importe máximo
    event = make_event("stock.reserved", amount=MAX_AMOUNT)
    await service.charge_payment(session, event)

    # Comprueba el estado del pago
    payment = await session.get(Payment, event.order_id)
    assert payment is not None
    assert payment.status == "completed"


async def test_charge_payment_bajo_el_maximo_escribe_payment_completed(session: AsyncSession) -> None:
    """Un pago completado escribe payment.completed en el outbox con los datos del evento recibido."""

    # Cobra 50 euros
    event = make_event("stock.reserved")
    await service.charge_payment(session, event)

    # Comprueba que el outbox tiene un único payment.completed con los mismos campos del evento
    events = await outbox_events(session)
    assert [(row.event_type, row.payload) for row in events] == [
        ("payment.completed", {**event.model_dump(mode="json"), "event_type": "payment.completed"})
    ]


async def test_charge_payment_sobre_el_maximo_marca_failed(session: AsyncSession) -> None:
    """Un importe por encima del máximo deja el pago en failed."""

    # Intenta cobrar un euro más que el máximo
    event = make_event("stock.reserved", amount=MAX_AMOUNT + 1)
    await service.charge_payment(session, event)

    # Comprueba el estado del pago
    payment = await session.get(Payment, event.order_id)
    assert payment is not None
    assert payment.status == "failed"


async def test_charge_payment_sobre_el_maximo_escribe_payment_failed(session: AsyncSession) -> None:
    """Un pago rechazado escribe payment.failed en el outbox."""

    # Intenta cobrar un euro más que el máximo
    await service.charge_payment(session, make_event("stock.reserved", amount=MAX_AMOUNT + 1))

    # Comprueba que el outbox tiene un único payment.failed
    events = await outbox_events(session)
    assert [row.event_type for row in events] == ["payment.failed"]


async def test_charge_payment_repetido_guarda_un_solo_pago(session: AsyncSession) -> None:
    """El mismo stock.reserved dos veces guarda un solo pago."""

    # Cobra dos veces con el mismo evento, como si llegara repetido
    event = make_event("stock.reserved")
    await service.charge_payment(session, event)
    await service.charge_payment(session, event)

    # Comprueba que solo hay un pago
    assert await session.scalar(select(func.count()).select_from(Payment)) == 1


async def test_charge_payment_repetido_escribe_un_solo_evento(session: AsyncSession) -> None:
    """El mismo stock.reserved dos veces escribe un solo payment.completed."""

    # Cobra dos veces con el mismo evento, como si llegara repetido
    event = make_event("stock.reserved")
    await service.charge_payment(session, event)
    await service.charge_payment(session, event)

    # Comprueba que el outbox tiene un único evento
    events = await outbox_events(session)
    assert [row.event_type for row in events] == ["payment.completed"]
