# Lógica de stock: leer un producto y reservar unidades para un pedido junto a su evento en la outbox.
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OutboxEvent, Product, Reservation
from app.schemas import OrderEvent


async def get_product(session: AsyncSession, product_id: str) -> Product | None:
    """Devuelve el producto, o None si no existe."""

    return await session.get(Product, product_id)


async def reserve_stock(session: AsyncSession, event: OrderEvent) -> None:
    """Reserva las unidades del pedido y escribe stock.reserved en la outbox, todo en la misma transacción."""

    async with session.begin():
        # Inserta la reserva; si ya existía, el evento es repetido y no se hace nada más
        insert_reservation = (
            insert(Reservation)
            .values(order_id=event.order_id, product_id=event.product_id, quantity=event.quantity, status="reserved")
            .on_conflict_do_nothing(index_elements=[Reservation.order_id])
            .returning(Reservation.order_id)
        )
        if await session.scalar(insert_reservation) is None:
            return

        # Descuenta las unidades solo si hay suficientes (si el producto no existe, tampoco toca ninguna fila)
        discount_units = (
            update(Product)
            .where(Product.id == event.product_id, Product.available >= event.quantity)
            .values(available=Product.available - event.quantity)
            .returning(Product.id)
        )
        reserved = await session.scalar(discount_units)

        # Si no hay unidades suficientes actualiza el estado de la reserva creada a failed. Al no eliminarla cualquier evento
        # repetido se comprueba gracias a este registro que ya existe. Esto nos da idempotencia.
        if reserved is None:
            await session.execute(update(Reservation).where(Reservation.order_id == event.order_id).values(status="failed"))
            return

        # Si todo ha ido bien escribe el evento de stock reservado en la tabla outbox del servicio
        reserved_event = event.model_copy(update={"event_type": "stock.reserved"})
        session.add(OutboxEvent(event_type=reserved_event.event_type, payload=reserved_event.model_dump(mode="json")))
