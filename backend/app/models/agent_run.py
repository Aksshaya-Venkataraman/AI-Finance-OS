from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base, utcnow

JSONType = JSON().with_variant(JSONB(), "postgresql")


class AgentRun(Base):
    """One assistant question: which agents ran, what they found, and the answer."""

    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    question: Mapped[str] = mapped_column(String(1000))
    intents: Mapped[list[str]] = mapped_column(JSONType)
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSONType)
    answer: Mapped[str] = mapped_column(Text)
    llm_used: Mapped[str] = mapped_column(String(64))
    request_id: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
