# Security

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting (Security → Report a vulnerability) rather
than a public issue.

## Controls

| Concern | Control |
|---|---|
| Secrets | Environment variables only; `.env` git-ignored and created with mode 600; weak or placeholder `SECRET_KEY` refused at start-up; gitleaks scans the full history in CI |
| Passwords | Argon2id; minimum 12 characters; legacy bcrypt hashes verified once, then upgraded; constant-time path for unknown emails |
| Tokens | PyJWT, HS256 pinned (no `none`/algorithm confusion), issuer, type and expiry required; deactivated users rejected on every request |
| Password reset | Token is only emailed, never returned by the API; stored as SHA-256; single use; 30-minute expiry; identical response for unknown emails; rate-limited |
| Authorisation | Every finance query is filtered by owner in the data layer; another user's IDs return 404; admin routes require `is_superuser`; mass-assignment blocked (`extra="forbid"`) |
| Input validation | Strict schemas, decimal money with fixed precision, category/type allow-lists, `<`/`>`/control characters rejected in free text, CSV size/row limits, 1 MB body limit |
| Abuse | Rate limits per IP (login, register, reset) and per user (API, assistant), shared via Redis |
| LLM | Off by default; only computed facts for the current user are sent; no tools; prompt-injection rules; failure falls back to a local template |
| Transport & headers | Caddy TLS + HSTS, CSP `default-src 'none'`, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, `no-store` |
| CORS | Explicit allow-list (`CORS_ORIGINS`); wildcard refused; no credentials |
| Production mode | Docs disabled, `debug=False`, generic 500 responses, SQL echo off, trusted-host check |
| Infrastructure | Non-root read-only containers, all capabilities dropped, internal network for PostgreSQL/Redis, non-superuser database role, SCRAM auth |
| Dependencies | Hash-locked `requirements.txt`, pip-audit + Bandit in CI, Dependabot weekly |
