# Punto de entrada de la API de orders: la app, su lifespan (crea las tablas), /health y las rutas.
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import Base, engine
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Crea las tablas al arrancar y cierra el pool de conexiones al apagar."""

    # Crea las tablas que falten (sin migraciones: los modelos llegan importados a través de las rutas)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # A partir de aquí la API atiende peticiones
    yield

    # Al apagar, cierra las conexiones del pool
    await engine.dispose()


# App global (la que arranca uvicorn con app.main:app) con las rutas de pedidos
app = FastAPI(title="OrderSaga Orders Service", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Comprueba que la API está viva."""

    return {"status": "ok"}
