from datetime import date, timedelta

from test_finance_api import add_tx, make_account

from backend.app.agents.llm import LLMError
from backend.app.core.config import settings
from backend.app.core.rate_limit import reset_limits
from backend.app.main import app
from backend.app.services.assistant_service import get_composer


def seed(client, headers):
    account = make_account(client, headers)
    today = date.today()
    add_tx(client, headers, account["id"], "-80.00", category="dining", description="Restaurant", day=today)
    add_tx(
        client,
        headers,
        account["id"],
        "2400.00",
        category="income",
        description="Salary",
        day=today.replace(day=1) - timedelta(days=20),
    )
    client.put("/api/v1/budgets/dining", json={"monthly_limit": "50"}, headers=headers)


def test_ask_runs_agents_and_stores_the_run(client, auth):
    seed(client, auth)
    resp = client.post("/api/v1/assistant/ask", json={"question": "Am I over budget this month?"}, headers=auth)
    assert resp.status_code == 201, resp.text
    run = resp.json()
    assert run["intents"] == ["budget"]
    assert run["llm_used"] == "template"
    assert "over budget" in run["answer"]
    assert run["steps"][0]["facts"]["budgets"][0]["status"] == "over"
    assert client.get(f"/api/v1/assistant/runs/{run['id']}", headers=auth).json()["answer"] == run["answer"]


def test_overview_question_uses_every_agent(client, auth):
    seed(client, auth)
    run = client.post("/api/v1/assistant/ask", json={"question": "How am I doing?"}, headers=auth).json()
    assert [s["agent"] for s in run["steps"]] == ["spending", "budget", "portfolio", "cashflow", "anomaly"]


def test_llm_failure_falls_back_to_template(client, auth):
    class Down:
        name = "anthropic:test"

        def compose(self, question, results):
            raise LLMError("unavailable")

    app.dependency_overrides[get_composer] = lambda: Down()
    run = client.post("/api/v1/assistant/ask", json={"question": "Where did my money go?"}, headers=auth).json()
    assert run["llm_used"] == "template (llm unavailable)"


def test_runs_are_private(client, auth, other_auth):
    run = client.post("/api/v1/assistant/ask", json={"question": "Any unusual charges?"}, headers=auth).json()
    assert client.get(f"/api/v1/assistant/runs/{run['id']}", headers=other_auth).status_code == 404
    assert client.get("/api/v1/assistant/runs", headers=other_auth).json() == []
    assert len(client.get("/api/v1/assistant/runs", headers=auth).json()) == 1


def test_agents_never_see_other_users_data(client, auth, other_auth):
    seed(client, other_auth)
    run = client.post("/api/v1/assistant/ask", json={"question": "Where did my money go?"}, headers=auth).json()
    assert run["steps"][0]["facts"]["month_to_date_spend"] == 0.0


def test_question_validation(client, auth):
    for question in ["", "hi", "x" * 1001, "bad\x00byte"]:
        assert client.post("/api/v1/assistant/ask", json={"question": question}, headers=auth).status_code == 422


def test_assistant_rate_limit(client, auth, monkeypatch):
    monkeypatch.setattr(settings, "ASSISTANT_RATE_LIMIT", "2/hour")
    reset_limits()
    codes = [client.post("/api/v1/assistant/ask", json={"question": "Spending?"}, headers=auth).status_code for _ in range(3)]
    assert codes == [201, 201, 429]
