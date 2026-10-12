# Tests de los endpoints HTTP de pedidos: creación, validación de la entrada y lectura.
import uuid

import httpx

# Cuerpo válido para crear un pedido
ORDER_BODY = {"product_id": "teclado", "quantity": 2, "amount": 50}


async def test_post_orders_responde_201_en_pending(client: httpx.AsyncClient) -> None:
    """Crear un pedido válido responde 201 con el pedido en pending."""

    response = await client.post("/orders", json=ORDER_BODY)
    assert response.status_code == 201
    assert response.json()["status"] == "pending"


async def test_post_orders_con_quantity_0_responde_422(client: httpx.AsyncClient) -> None:
    """Un pedido con quantity 0 se rechaza."""

    response = await client.post("/orders", json={**ORDER_BODY, "quantity": 0})
    assert response.status_code == 422


async def test_post_orders_con_amount_0_responde_422(client: httpx.AsyncClient) -> None:
    """Un pedido con amount 0 se rechaza."""

    response = await client.post("/orders", json={**ORDER_BODY, "amount": 0})
    assert response.status_code == 422


async def test_post_orders_con_product_id_vacio_responde_422(client: httpx.AsyncClient) -> None:
    """Un pedido con product_id vacío se rechaza."""

    response = await client.post("/orders", json={**ORDER_BODY, "product_id": ""})
    assert response.status_code == 422


async def test_get_order_devuelve_el_pedido(client: httpx.AsyncClient) -> None:
    """Leer un pedido existente lo devuelve tal y como se creó."""

    # Crea el pedido por la API
    created = (await client.post("/orders", json=ORDER_BODY)).json()

    # Lo lee por su id
    response = await client.get(f"/orders/{created['id']}")

    # Comprueba que devuelve el mismo pedido
    assert response.status_code == 200
    assert response.json() == created


async def test_get_order_inexistente_responde_404(client: httpx.AsyncClient) -> None:
    """Leer un pedido que no existe responde 404."""

    response = await client.get(f"/orders/{uuid.uuid7()}")
    assert response.status_code == 404
