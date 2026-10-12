# Conexión a PostgreSQL: engine, fábrica de sesiones, Base de los modelos y sesión por petición.
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

# Un único engine (pool de conexiones) por proceso y su fábrica de sesiones
engine = create_async_engine(get_settings().database_url)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Clase base de todos los modelos."""


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Abre una sesión para la petición y la cierra al terminar."""

    async with SessionFactory() as session:
        yield session
