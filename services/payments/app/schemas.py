# Esquemas de la API (pago de un pedido) y del evento que se recibe y se publica en Kafka.
import uuid

from pydantic import BaseModel, ConfigDict


class PaymentOut(BaseModel):
    """Pago de un pedido tal y como lo devuelve la API."""

    model_config = ConfigDict(from_attributes=True)

    order_id: uuid.UUID
    amount: int
    status: str


class OrderEvent(BaseModel):
    """Evento de la saga: todos los servicios publican y reciben estos mismos campos."""

    event_type: str
    order_id: uuid.UUID
    product_id: str
    quantity: int
    amount: int
