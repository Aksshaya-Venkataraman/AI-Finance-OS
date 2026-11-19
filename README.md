# AI-Finance-OS

A modular FastAPI backend for AI-driven personal finance. Users record accounts, transactions,
budgets and investments, then ask questions in plain English. A multi-agent workflow routes each
question to specialist agents, which compute the answer from the user's own data. A language
model (optional) only phrases the result.

```mermaid
flowchart LR
    client([Client]) -- HTTPS --> caddy[Caddy] --> api
    subgraph api [FastAPI application]
        direction TB
        A[API layer<br/>routers, auth, rate limits] --> S[Service layer<br/>business rules]
        S --> D[Data layer<br/>per-user repositories]
        S --> O[Agent layer<br/>orchestrator]
        O --> R{Intent router}
        R --> SP[Spending] & BU[Budget] & PO[Portfolio] & CF[Cash-flow] & AN[Anomaly]
        O --> C[Composer<br/>template or Claude]
    end
    D --> pg[(PostgreSQL)]
    A --> redis[(Redis<br/>rate limits)]
```

## Layers

| Layer | Package | Responsibility |
|---|---|---|
| API | `backend/app/api` | HTTP routes, request validation, auth dependencies, rate limits |
| Service | `backend/app/services` | Business rules: accounts, transactions, CSV import, budgets, holdings, assistant runs, auth |
| Data | `backend/app/data` | `FinanceRepository` (every query filtered by owner) and read-only `FinanceSnapshot` for agents |
| Agent | `backend/app/agents` | Intent router, five specialist agents, orchestrator, LLM composer |
| Core | `backend/app/core` | Settings, security (Argon2id, JWT), middleware, rate limiting |

## The agents

| Agent | Answers | Method |
|---|---|---|
| **Spending** | "Where did my money go?" | Month-to-date spend by category vs the same days last month, top merchants |
| **Budget** | "Am I over budget?" | Spend vs monthly limits, month-end projection, 50/30/20 check on last month's income |
| **Portfolio** | "Is my portfolio diversified?" | Market value, unrealised gain, allocation, largest position, Herfindahl-based effective number of positions |
| **Cash-flow** | "Can I afford…? What's my savings rate?" | 6-month income/spending, savings rate, linear-trend projection, emergency-fund months |
| **Anomaly** | "Anything suspicious?" | Robust (median/MAD) z-score per category over 6 months, possible duplicate charges |

The router picks agents by keyword; an open question ("How am I doing?") runs all five. Each agent
returns a summary, alerts and structured facts, and every run is stored (`/assistant/runs`) with
its full trace. Agents work on a read-only snapshot of one user's data, so they can't write to
the database or see anyone else's records. A failing agent is reported but doesn't break the
answer.

**LLM integration.** With `LLM_PROVIDER=anthropic`, Claude writes the reply from the agents'
facts. The system prompt forbids inventing numbers and following instructions found inside user
data, and the model has no tools. If the API is unreachable, the deterministic template is used
instead. With `LLM_PROVIDER=none` (default), no data leaves the server.

## Quick start

```bash
python3 scripts/generate_env.py            # .env with random secrets (chmod 600, git-ignored)
docker compose up -d --build --wait        # Caddy + API + PostgreSQL + Redis, migrations run automatically
curl -k https://localhost/health
```

For a real server, point DNS at it and run `python3 scripts/generate_env.py --domain finance.example.com`.
Caddy obtains a Let's Encrypt certificate automatically.

### Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env    # set SECRET_KEY, DATABASE_URL, ENVIRONMENT=development, ENABLE_DOCS=true, ALLOWED_HOSTS=localhost
alembic upgrade head
uvicorn backend.app.main:app --reload
```

Swagger UI is at `/docs` when `ENABLE_DOCS=true` (it is off in production).

## Example

```bash
API=https://localhost/api/v1
curl -sk $API/auth/register -H 'Content-Type: application/json' \
  -d '{"full_name":"Aksshaya","email":"me@example.com","password":"a-long-passphrase-1"}'
TOKEN=$(curl -sk $API/auth/login -d 'username=me@example.com&password=a-long-passphrase-1' | jq -r .access_token)
AUTH="Authorization: Bearer $TOKEN"

curl -sk $API/accounts -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"name":"Current","account_type":"current","currency":"GBP","opening_balance":"1200.00"}'
curl -sk "$API/transactions/import?account_id=1" -H "$AUTH" -F file=@statement.csv   # date,amount,description,category
curl -sk -X PUT $API/budgets/dining -H "$AUTH" -H 'Content-Type: application/json' -d '{"monthly_limit":"150"}'
curl -sk $API/assistant/ask -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"question":"Am I over budget this month and is anything unusual?"}'
```

## API overview

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/login` (OAuth2 form), `POST /auth/forgot-password`, `POST /auth/reset-password` |
| Users | `GET/PUT /users/me`, `POST /users/change-password`, `POST /users/deactivate` |
| Accounts | `GET/POST /accounts`, `DELETE /accounts/{id}` (balances included) |
| Transactions | `GET/POST /transactions` (filters + pagination), `PATCH/DELETE /transactions/{id}`, `POST /transactions/import` (CSV, all-or-nothing) |
| Budgets | `GET /budgets` (status for this month), `PUT/DELETE /budgets/{category}` |
| Holdings | `GET/POST /holdings`, `PATCH/DELETE /holdings/{id}` |
| Assistant | `POST /assistant/ask`, `GET /assistant/runs`, `GET /assistant/runs/{id}` |
| Admin | `GET /admin/users` (superusers only) |
| Ops | `GET /health`, `GET /ready` |

All paths except ops are under `/api/v1`. Money is exchanged as decimal strings and stored as `NUMERIC`.

## Testing

```bash
pytest                                   # 76 tests on SQLite
TEST_POSTGRES_URL=postgresql+psycopg://user:pass@localhost/empty_db pytest tests/test_migrations.py
```

CI runs ruff, Bandit, pip-audit, gitleaks (full history), the test suite with migrations on
PostgreSQL, and a Docker Compose smoke test through Caddy.

## Upgrading from v1

- Run `alembic upgrade head`. It adds the finance and agent tables, and switches password-reset
  tokens to hashed storage. Any outstanding reset tokens are invalidated.
- Existing bcrypt passwords keep working and are re-hashed with Argon2id at the next login.
- `SECRET_KEY` must now be at least 32 random characters. `ALGORITHM` is ignored because HS256
  is pinned in code. Access tokens issued by v1 stop working, so users simply log in again.
- `postgresql://` URLs are switched to the psycopg 3 driver automatically. psycopg2 is no longer
  needed.

See [SECURITY.md](SECURITY.md) for the security controls.
