# Consumidor de Kafka: lee los eventos de los topics de los que depende orders y confirma cada offset tras procesarlo.
import asyncio
import json
import logging
from typing import Any

from aiokafka import AIOKafkaConsumer

from app.config import get_settings
from app.db import SessionFactory, engine
from app.events_handlers import handle_event

# Topics que escucha orders: payments para confirmar y stock para cancelar
TOPICS = ["payments", "stock"]

logger = logging.getLogger("app.events_consumer")


def deserialize_value(value: bytes) -> dict[str, Any]:
    """Convierte el JSON en bytes del mensaje a un diccionario."""

    data: dict[str, Any] = json.loads(value)
    return data


async def main() -> None:
    """Arranca el consumidor de Kafka y procesa los mensajes uno a uno hasta que se pare el proceso."""

    # Una línea de log por evento procesado
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    # Consumidor del grupo orders que confirma los offsets a mano, y empieza por el principio si el grupo es nuevo
    consumer = AIOKafkaConsumer(
        *TOPICS,
        bootstrap_servers=get_settings().kafka_bootstrap_servers,
        group_id="orders",
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        value_deserializer=deserialize_value,
    )
    await consumer.start()

    # Confirma el offset solo cuando la transacción del handler se ha confirmado; si el handler falla, el proceso
    # muere sin confirmarlo y el mensaje se reprocesa al reiniciar
    try:
        async for message in consumer:
            async with SessionFactory() as session:
                await handle_event(session, message.value)
            await consumer.commit()
            logger.info("Procesado %s del pedido %s", message.value["event_type"], message.value["order_id"])
    finally:
        await consumer.stop()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
