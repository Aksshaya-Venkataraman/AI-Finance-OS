from datetime import date
from functools import lru_cache

from backend.app.agents.llm import AnthropicComposer, Composer, TemplateComposer
from backend.app.agents.orchestrator import Orchestrator
from backend.app.core.config import settings
from backend.app.core.middleware import request_id_ctx
from backend.app.data.repositories import FinanceRepository
from backend.app.data.snapshot import build_snapshot
from backend.app.models.agent_run import AgentRun
from backend.app.services.errors import NotFoundError


@lru_cache
def get_composer() -> Composer:
    if settings.llm_enabled and settings.ANTHROPIC_API_KEY is not None:
        return AnthropicComposer(
            api_key=settings.ANTHROPIC_API_KEY.get_secret_value(),
            model=settings.LLM_MODEL,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
    return TemplateComposer()


def ask(repo: FinanceRepository, question: str, composer: Composer, today: date | None = None) -> AgentRun:
    snapshot = build_snapshot(repo, as_of=today)
    result = Orchestrator(composer=composer).run(question, snapshot)
    run = AgentRun(
        owner_id=repo.owner_id,
        question=question,
        intents=result.intents,
        steps=[step.to_dict() for step in result.steps],
        answer=result.answer,
        llm_used=result.composer,
        request_id=request_id_ctx.get(),
    )
    repo.add(run)
    repo.db.commit()
    return run


def get_run(repo: FinanceRepository, run_id: int) -> AgentRun:
    run = repo.get_agent_run(run_id)
    if run is None:
        raise NotFoundError("Assistant run not found")
    return run
