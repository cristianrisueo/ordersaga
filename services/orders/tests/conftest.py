# Fixtures de los tests de orders: PostgreSQL real en un contenedor, tablas limpias por test, sesión y cliente HTTP.
import os
import uuid
from collections.abc import AsyncGenerator, Iterator

import httpx
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from testcontainers.community.postgres import PostgresContainer

# Arranca PostgreSQL y apunta DATABASE_URL a él antes de importar app: app/db.py crea el engine al importarse
postgres = PostgresContainer("postgres:18", driver="asyncpg")
postgres.start()
os.environ["DATABASE_URL"] = postgres.get_connection_url()

from app.db import Base, SessionFactory, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import OutboxEvent  # noqa: E402
from app.schemas import OrderEvent  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def stop_postgres() -> Iterator[None]:
    """Para el contenedor de PostgreSQL al terminar la sesión."""

    yield
    postgres.stop()


@pytest.fixture(scope="session", autouse=True)
async def create_tables(stop_postgres: None) -> AsyncGenerator[None]:
    """Crea las tablas una vez por sesión y cierra el pool de conexiones al terminar."""

    # Crea las tablas de todos los modelos
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Los tests se ejecutan aquí
    yield

    # Al terminar, cierra las conexiones del pool
    await engine.dispose()


@pytest.fixture(autouse=True)
async def clean_tables(create_tables: None) -> None:
    """Vacía todas las tablas antes de cada test."""

    tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession]:
    """Abre una sesión de base de datos para el test."""

    async with SessionFactory() as session:
        yield session


@pytest.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient]:
    """Cliente HTTP contra la app en memoria (sin lifespan: las tablas las ponen las fixtures)."""

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client


def make_event(event_type: str, order_id: uuid.UUID) -> OrderEvent:
    """Construye un evento de prueba para un pedido."""

    return OrderEvent(event_type=event_type, order_id=order_id, product_id="teclado", quantity=2, amount=50)


async def outbox_events(session: AsyncSession) -> list[OutboxEvent]:
    """Devuelve las filas del outbox en orden de creación."""

    return list(await session.scalars(select(OutboxEvent).order_by(OutboxEvent.id)))
