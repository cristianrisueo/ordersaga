# Configuración del servicio payments, leída de variables de entorno.
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración del servicio; los valores por defecto son los de compose."""

    database_url: str = "postgresql+asyncpg://payments:payments@db-payments:5432/payments"
    kafka_bootstrap_servers: str = "kafka:9092"
    max_amount: int = 1000


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración, leída una sola vez por proceso."""

    return Settings()
