# Tests de los endpoints HTTP de stock: lectura de las unidades disponibles de un producto.
import httpx


async def test_get_stock_teclado_devuelve_5(client: httpx.AsyncClient) -> None:
    """El teclado del catálogo inicial tiene 5 unidades."""

    response = await client.get("/stock/teclado")
    assert response.status_code == 200
    assert response.json() == {"product_id": "teclado", "available": 5}


async def test_get_stock_producto_inexistente_responde_404(client: httpx.AsyncClient) -> None:
    """Un producto que no está en el catálogo responde 404."""

    response = await client.get("/stock/raton")
    assert response.status_code == 404
