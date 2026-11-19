from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
import pytest
from conftest import PASSWORD, login, register
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.core.rate_limit import reset_limits
from backend.app.database.session import SessionLocal
from backend.app.models.password_reset_token import PasswordResetToken
from backend.app.models.user import User
from backend.app.services import auth_service


def _user(email: str) -> User:
    with SessionLocal() as db:
        return db.scalar(select(User).where(User.email == email))


def test_register_login_and_profile(client):
    created = register(client, "Alice@Example.com", name="Alice")
    assert created["email"] == "alice@example.com"
    assert "hashed_password" not in created
    me = client.get("/api/v1/users/me", headers=login(client, "alice@example.com")).json()
    assert me["full_name"] == "Alice"


def test_passwords_hashed_with_argon2id(client):
    register(client, "hash@example.com")
    stored = _user("hash@example.com").hashed_password
    assert stored.startswith("$argon2id$")
    assert PASSWORD not in stored


def test_duplicate_registration_is_generic(client):
    register(client, "dup@example.com")
    resp = client.post("/api/v1/auth/register", json={"full_name": "X", "email": "dup@example.com", "password": PASSWORD})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Registration failed"


@pytest.mark.parametrize("password", ["short", "aaaaaaaaaaaaaaaaaa", "x" * 129])
def test_weak_passwords_rejected(client, password):
    resp = client.post("/api/v1/auth/register", json={"full_name": "W", "email": "w@example.com", "password": password})
    assert resp.status_code == 422


def test_mass_assignment_blocked(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={"full_name": "M", "email": "m@example.com", "password": PASSWORD, "is_superuser": True},
    )
    assert resp.status_code == 422


def test_login_errors_do_not_reveal_accounts(client):
    register(client, "bob@example.com")
    wrong = client.post("/api/v1/auth/login", data={"username": "bob@example.com", "password": "wrong-password-1"})
    ghost = client.post("/api/v1/auth/login", data={"username": "ghost@example.com", "password": PASSWORD})
    assert wrong.status_code == ghost.status_code == 401
    assert wrong.json() == ghost.json()


def test_legacy_bcrypt_hash_still_works_and_is_upgraded(client):
    register(client, "legacy@example.com")
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "legacy@example.com"))
        user.hashed_password = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode()
        db.commit()
    login(client, "legacy@example.com")
    assert _user("legacy@example.com").hashed_password.startswith("$argon2id$")


def _token(**overrides) -> str:
    now = datetime.now(UTC)
    claims = {"sub": "1", "iat": now, "exp": now + timedelta(minutes=5), "iss": settings.PROJECT_NAME, "typ": "access"}
    claims.update(overrides)
    return jwt.encode(claims, settings.SECRET_KEY.get_secret_value(), algorithm="HS256")


@pytest.mark.parametrize(
    "token",
    [
        "not-a-token",
        _token(exp=datetime.now(UTC) - timedelta(seconds=5)),
        _token(iss="someone-else"),
        _token(typ="refresh"),
        jwt.encode({"sub": "1"}, "a-completely-different-signing-key!!", algorithm="HS256"),
        "eyJhbGciOiJub25lIn0.eyJzdWIiOiIxIn0.",
    ],
    ids=["garbage", "expired", "wrong-issuer", "wrong-type", "wrong-key", "alg-none"],
)
def test_invalid_tokens_rejected(client, token):
    register(client, "victim@example.com")
    assert client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_forgot_password_never_returns_the_token(client, monkeypatch):
    sent = []
    monkeypatch.setattr("backend.app.api.auth.send_password_reset", lambda email, token: sent.append((email, token)))
    register(client, "reset@example.com")
    known = client.post("/api/v1/auth/forgot-password", json={"email": "reset@example.com"})
    unknown = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert len(sent) == 1
    assert sent[0][1] not in known.text
    with SessionLocal() as db:
        stored = db.scalar(select(PasswordResetToken))
    assert stored.token_hash != sent[0][1]
    assert len(stored.token_hash) == 64


def test_password_reset_flow_is_single_use(client, monkeypatch):
    sent = []
    monkeypatch.setattr("backend.app.api.auth.send_password_reset", lambda email, token: sent.append(token))
    register(client, "flow@example.com")
    client.post("/api/v1/auth/forgot-password", json={"email": "flow@example.com"})
    new_password = "a-brand-new-password-42"
    body = {"token": sent[0], "new_password": new_password}
    assert client.post("/api/v1/auth/reset-password", json=body).status_code == 200
    login(client, "flow@example.com", new_password)
    assert client.post("/api/v1/auth/reset-password", json=body).status_code == 400


def test_expired_reset_token_rejected(client):
    register(client, "late@example.com")
    with SessionLocal() as db:
        _, token = auth_service.create_password_reset_request(db, "late@example.com")
        record = db.scalar(select(PasswordResetToken))
        record.expires_at = record.expires_at - timedelta(hours=2)
        db.commit()
    resp = client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "another-password-77"})
    assert resp.status_code == 400


def test_login_is_rate_limited(client, monkeypatch):
    monkeypatch.setattr(settings, "LOGIN_RATE_LIMIT", "3/minute")
    reset_limits()
    form = {"username": "brute@example.com", "password": "guess-guess-guess"}
    codes = [client.post("/api/v1/auth/login", data=form).status_code for _ in range(4)]
    assert codes == [401, 401, 401, 429]
