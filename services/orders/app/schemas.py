# Esquemas de la API (entrada y salida de pedidos) y del evento que se publica en Kafka.
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OrderIn(BaseModel):
    """Datos para crear un pedido."""

    product_id: str = Field(min_length=1)
    quantity: int = Field(gt=0)
    amount: int = Field(gt=0)


class OrderOut(BaseModel):
    """Pedido tal y como lo devuelve la API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: str
    quantity: int
    amount: int
    status: str
    created_at: datetime


class OrderEvent(BaseModel):
    """Evento de la saga: todos los servicios publican estos mismos campos."""

    event_type: str
    order_id: uuid.UUID
    product_id: str
    quantity: int
    amount: int
