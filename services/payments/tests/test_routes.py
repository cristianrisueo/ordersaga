# Tests de los endpoints HTTP de pagos: lectura del pago de un pedido.
import uuid

import httpx
from conftest import make_event
from sqlalchemy.ext.asyncio import AsyncSession

from app import service


async def test_get_payment_devuelve_el_pago(client: httpx.AsyncClient, session: AsyncSession) -> None:
    """Leer el pago de un pedido cobrado lo devuelve con su importe y estado."""

    # Prepara un pedido cobrado
    event = make_event("stock.reserved")
    await service.charge_payment(session, event)

    # Lee su pago por la API
    response = await client.get(f"/payments/{event.order_id}")

    # Comprueba la respuesta
    assert response.status_code == 200
    assert response.json() == {"order_id": str(event.order_id), "amount": 50, "status": "completed"}


async def test_get_payment_inexistente_responde_404(client: httpx.AsyncClient) -> None:
    """Leer el pago de un pedido sin pago responde 404."""

    response = await client.get(f"/payments/{uuid.uuid7()}")
    assert response.status_code == 404
