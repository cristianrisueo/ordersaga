# Esquemas de la API (stock de un producto) y del evento que se recibe y se publica en Kafka.
import uuid

from pydantic import BaseModel


class StockOut(BaseModel):
    """Unidades disponibles de un producto tal y como las devuelve la API."""

    product_id: str
    available: int


class OrderEvent(BaseModel):
    """
    Evento de stock reservado: todos los servicios publican estos mismos campos. En un patrón
    Saga por orquestación, el evento publicado tiene los mismos campos en todos los servicios.
    """

    event_type: str
    order_id: uuid.UUID
    product_id: str
    quantity: int
    amount: int
