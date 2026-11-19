from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, StringConstraints


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=3, max_length=1000, pattern=r"^[^\x00-\x08\x0b\x0c\x0e-\x1f\x7f]+$")
    ]


class AgentStep(BaseModel):
    agent: str
    summary: str
    alerts: list[str]
    facts: dict[str, Any]


class AgentRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question: str
    intents: list[str]
    steps: list[AgentStep]
    answer: str
    llm_used: str
    request_id: str
    created_at: datetime
