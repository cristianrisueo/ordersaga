# Punto de entrada de la API de stock: la app, su lifespan (crea las tablas y carga el catálogo), /health y las rutas.
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.dialects.postgresql import insert

from app.db import Base, engine
from app.models import Product
from app.routes import router

# Catálogo inicial: unidades disponibles de cada producto
CATALOG = [
    {"id": "teclado", "available": 5},
    {"id": "monitor", "available": 1},
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Crea las tablas y carga el catálogo al arrancar, y cierra el pool de conexiones al apagar."""

    # Crea las tablas que falten (sin migraciones: importar Product registra todos los modelos)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Carga el catálogo; los productos que ya existen no se tocan, para no pisar sus unidades
    async with engine.begin() as conn:
        await conn.execute(insert(Product).values(CATALOG).on_conflict_do_nothing())

    # A partir de aquí la API atiende peticiones
    yield

    # Al apagar, cierra las conexiones del pool
    await engine.dispose()


# App global (la que arranca uvicorn con app.main:app) con las rutas de stock
app = FastAPI(title="OrderSaga Stock Service", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Comprueba que la API está viva."""

    return {"status": "ok"}
