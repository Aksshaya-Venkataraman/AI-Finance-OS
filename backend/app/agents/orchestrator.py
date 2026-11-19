"""Multi-agent workflow: route -> run specialists -> compose one answer."""

import logging
from dataclasses import dataclass

from backend.app.agents.anomaly import AnomalyAgent
from backend.app.agents.base import Agent, AgentResult
from backend.app.agents.budget import BudgetAgent
from backend.app.agents.cashflow import CashflowAgent
from backend.app.agents.llm import Composer, LLMError, TemplateComposer
from backend.app.agents.portfolio import PortfolioAgent
from backend.app.agents.router import route
from backend.app.agents.spending import SpendingAgent
from backend.app.data.snapshot import FinanceSnapshot

log = logging.getLogger(__name__)


def default_agents() -> dict[str, Agent]:
    agents: list[Agent] = [SpendingAgent(), BudgetAgent(), PortfolioAgent(), CashflowAgent(), AnomalyAgent()]
    return {agent.name: agent for agent in agents}


@dataclass
class OrchestrationResult:
    intents: list[str]
    steps: list[AgentResult]
    answer: str
    composer: str


class Orchestrator:
    def __init__(self, composer: Composer | None = None, agents: dict[str, Agent] | None = None) -> None:
        self.composer = composer or TemplateComposer()
        self.agents = agents or default_agents()
        self._fallback = TemplateComposer()

    def run(self, question: str, snapshot: FinanceSnapshot) -> OrchestrationResult:
        intents = [i for i in route(question) if i in self.agents]
        steps: list[AgentResult] = []
        for intent in intents:
            try:
                steps.append(self.agents[intent].run(snapshot))
            except Exception:  # one failing agent must not break the whole answer
                log.exception("agent %s failed", intent)
                steps.append(AgentResult(agent=intent, summary=f"The {intent} analysis could not be completed.", facts={}))

        try:
            answer, used = self.composer.compose(question, steps), self.composer.name
        except LLMError:
            answer, used = self._fallback.compose(question, steps), "template (llm unavailable)"
        return OrchestrationResult(intents=intents, steps=steps, answer=answer, composer=used)
