# Endpoints HTTP de pedidos: traducen la petición, llaman al service y devuelven la respuesta.
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import service
from app.db import get_session
from app.schemas import OrderIn, OrderOut

# Rutas bajo /orders y la sesión de base de datos que reciben
router = APIRouter(prefix="/orders", tags=["orders"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_order(data: OrderIn, session: SessionDep) -> OrderOut:
    """Crea un pedido en pending."""

    order = await service.create_order(session, data)
    return OrderOut.model_validate(order)


@router.get("/{order_id}")
async def get_order(order_id: uuid.UUID, session: SessionDep) -> OrderOut:
    """Devuelve un pedido, o 404 si no existe."""

    # Busca el pedido y responde 404 si no está
    order = await service.get_order(session, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado")

    return OrderOut.model_validate(order)
