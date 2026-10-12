# Endpoints HTTP de pagos: traducen la petición, llaman al service y devuelven la respuesta.
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import service
from app.db import get_session
from app.schemas import PaymentOut

# Rutas bajo /payments y la sesión de base de datos que reciben
router = APIRouter(prefix="/payments", tags=["payments"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("/{order_id}")
async def get_payment(order_id: uuid.UUID, session: SessionDep) -> PaymentOut:
    """Devuelve el pago de un pedido, o 404 si no existe."""

    # Busca el pago y responde 404 si no está
    payment = await service.get_payment(session, order_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pago no encontrado")

    return PaymentOut.model_validate(payment)
