"""Decides which specialist agents answer a question.

Keyword routing is deterministic, free and testable. A question that matches
nothing (e.g. "how am I doing?") gets the full overview from every agent.
"""

import re

INTENT_PATTERNS: dict[str, re.Pattern[str]] = {
    "spending": re.compile(r"\b(spen[dt]\w*|expens\w*|categor\w*|merchant\w*|where did (my|the) money)"),
    "budget": re.compile(r"\b(budget\w*|overspen\w*|limit\w*|50/30/20|allowance)"),
    "portfolio": re.compile(r"\b(portfolio\w*|invest\w*|holding\w*|stocks?|shares?|allocation|diversif\w*|returns?)\b"),
    "cashflow": re.compile(r"\b(cash ?flow|sav(e|es|ing|ings)|forecast\w*|next month|emergency|income|afford\w*)\b"),
    "anomaly": re.compile(r"\b(unusual|anomal\w*|suspicious|fraud\w*|duplicat\w*|strange|unexpected)"),
}
ALL_INTENTS = tuple(INTENT_PATTERNS)


def route(question: str) -> list[str]:
    text = question.lower()
    matched = [intent for intent, pattern in INTENT_PATTERNS.items() if pattern.search(text)]
    return matched or list(ALL_INTENTS)
