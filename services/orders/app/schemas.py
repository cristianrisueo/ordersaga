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
    """Pedido tal devuelto por la API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: str
    quantity: int
    amount: int
    status: str
    created_at: datetime


class OrderEvent(BaseModel):
    """
    Evento de creación de pedido: todos los servicios publican estos mismos campos. En un patrón
    Saga por orquestación, el evento publicado tiene los mismos campos en todos los servicios.
    """

    event_type: str
    order_id: uuid.UUID
    product_id: str
    quantity: int
    amount: int
