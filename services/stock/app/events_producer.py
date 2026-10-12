# Productor del outbox: publica en el topic stock los eventos de la tabla outbox y borra sus filas.
import asyncio
import json
import logging
from typing import Any

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionFactory, engine
from app.models import OutboxEvent

# Topic de destino, tamaño máximo de cada lote y pausa cuando la outbox está vacía
TOPIC = "stock"
BATCH_SIZE = 100
IDLE_SECONDS = 0.5

logger = logging.getLogger("app.events_producer")


def serialize_value(value: dict[str, Any]) -> bytes:
    """Convierte el payload del evento a JSON en bytes."""

    return json.dumps(value).encode()


def serialize_key(key: str) -> bytes:
    """Convierte la clave (el order_id) a bytes."""

    return key.encode()


async def publish_batch(producer: AIOKafkaProducer) -> int:
    """Publica un lote de la outbox y borra sus filas en una transacción; devuelve cuántos eventos publicó."""

    async with SessionFactory() as session, session.begin():
        # Bloquea hasta BATCH_SIZE filas, las más antiguas primero, saltando las que tenga bloqueadas otro proceso
        query = select(OutboxEvent).order_by(OutboxEvent.created_at).limit(BATCH_SIZE).with_for_update(skip_locked=True)
        events = (await session.scalars(query)).all()

        # Publica cada evento con su order_id como clave y borra su fila; si Kafka falla, la transacción se deshace
        for event in events:
            order_id = event.payload["order_id"]
            await producer.send_and_wait(TOPIC, value=event.payload, key=order_id)
            await session.delete(event)
            logger.info("Publicado %s del pedido %s", event.event_type, order_id)

    return len(events)


async def main() -> None:
    """Arranca el productor de Kafka y recorre la outbox en bucle hasta que se pare el proceso."""

    # Una línea de log por evento publicado
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    # Productor que espera la confirmación de todas las réplicas antes de dar un envío por bueno
    producer = AIOKafkaProducer(
        bootstrap_servers=get_settings().kafka_bootstrap_servers,
        acks="all",
        value_serializer=serialize_value,
        key_serializer=serialize_key,
    )
    await producer.start()

    # Si Kafka falla, el lote ya se ha deshecho y se reintenta; si no había nada que publicar, espera un poco
    try:
        while True:
            try:
                published = await publish_batch(producer)
            except KafkaError:
                logger.exception("Fallo al publicar en Kafka: el lote se reintentará")
                published = 0
            if published == 0:
                await asyncio.sleep(IDLE_SECONDS)
    finally:
        await producer.stop()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
