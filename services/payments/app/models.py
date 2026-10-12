# Esquemas SQL: los pagos por pedido y la outbox con los eventos pendientes de publicar.
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Payment(Base):
    """Pago de un pedido, uno por pedido; amount va en euros enteros y status es completed o failed."""

    __tablename__ = "payments"

    order_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    amount: Mapped[int]
    status: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OutboxEvent(Base):
    """Evento guardado junto al cambio que lo origina, a la espera de que el productor lo publique."""

    __tablename__ = "outbox"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    event_type: Mapped[str]
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
