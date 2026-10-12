# Endpoints HTTP de stock: traducen la petición, llaman al service y devuelven la respuesta.
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import service
from app.db import get_session
from app.schemas import StockOut

# Rutas bajo /stock y la sesión de base de datos que reciben
router = APIRouter(prefix="/stock", tags=["stock"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("/{product_id}")
async def get_stock(product_id: str, session: SessionDep) -> StockOut:
    """Devuelve las unidades disponibles de un producto, o 404 si no existe."""

    # Busca el producto y responde 404 si no está
    product = await service.get_product(session, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")

    return StockOut(product_id=product.id, available=product.available)
