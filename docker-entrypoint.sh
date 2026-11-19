#!/bin/sh
# Apply database migrations, then start the API.
set -eu

alembic upgrade head

# FORWARDED_ALLOW_IPS lists the proxies whose X-Forwarded-For header is
# trusted (used for per-client rate limits). Only widen it when this port is
# reachable from nothing but the reverse proxy.
exec uvicorn backend.app.main:app \
  --host 0.0.0.0 --port 8000 \
  --proxy-headers --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}" \
  --no-server-header --no-access-log
