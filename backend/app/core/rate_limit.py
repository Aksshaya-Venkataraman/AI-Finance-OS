"""Rate limits backed by `limits` (memory for one process, Redis when scaled out)."""

import time
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from limits import parse
from limits.storage import storage_from_string
from limits.strategies import MovingWindowRateLimiter

from backend.app.core.config import settings
from backend.app.core.dependencies import get_current_user
from backend.app.models.user import User

_limiter = MovingWindowRateLimiter(storage_from_string(settings.RATE_LIMIT_STORAGE_URI.get_secret_value()))


def _hit(limit_value: str, scope: str, key: str) -> None:
    item = parse(limit_value)
    if not _limiter.hit(item, scope, key):
        reset_at, _ = _limiter.get_window_stats(item, scope, key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
            headers={"Retry-After": str(max(1, int(reset_at - time.time())))},
        )


def reset_limits() -> None:
    _limiter.storage.reset()


def limit_by_ip(scope: str, setting_name: str) -> Callable[[Request], None]:
    def dependency(request: Request) -> None:
        # request.client honours X-Forwarded-For only from FORWARDED_ALLOW_IPS.
        ip = request.client.host if request.client else "unknown"
        _hit(getattr(settings, setting_name), scope, ip)

    return dependency


def limit_by_user(scope: str, setting_name: str) -> Callable[..., None]:
    def dependency(current_user: User = Depends(get_current_user)) -> None:
        _hit(getattr(settings, setting_name), scope, f"user:{current_user.id}")

    return dependency
