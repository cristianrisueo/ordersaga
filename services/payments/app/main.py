# Punto de entrada de la API de payments: la app, su lifespan (crea las tablas), /health y las rutas.
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

# Registra los modelos en Base.metadata para create_all, sin depender de los imports de las rutas
from app import models  # noqa: F401
from app.db import Base, engine
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Crea las tablas al arrancar y cierra el pool de conexiones al apagar."""

    # Crea las tablas que falten (sin migraciones)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # A partir de aquí la API atiende peticiones
    yield

    # Al apagar, cierra las conexiones del pool
    await engine.dispose()


# App global (la que arranca uvicorn con app.main:app) con las rutas de pagos
app = FastAPI(title="OrderSaga Payments Service", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Comprueba que la API está viva."""

    return {"status": "ok"}
