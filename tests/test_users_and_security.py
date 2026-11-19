import pytest
from conftest import PASSWORD, login, register
from pydantic import ValidationError
from sqlalchemy import select

from backend.app.core.config import Settings
from backend.app.database.session import SessionLocal
from backend.app.models.user import User


def test_update_profile_and_change_password(client, auth):
    resp = client.put("/api/v1/users/me", json={"full_name": "New Name"}, headers=auth)
    assert resp.json()["full_name"] == "New Name"
    body = {"current_password": PASSWORD, "new_password": "a-new-long-password-9"}
    assert client.post("/api/v1/users/change-password", json=body, headers=auth).status_code == 200
    login(client, "owner@example.com", "a-new-long-password-9")


def test_change_password_requires_current_password(client, auth):
    body = {"current_password": "wrong-password-0", "new_password": "a-new-long-password-9"}
    assert client.post("/api/v1/users/change-password", json=body, headers=auth).status_code == 400


def test_email_change_cannot_take_another_users_address(client, auth, other_auth):
    resp = client.put("/api/v1/users/me", json={"email": "intruder@example.com"}, headers=auth)
    assert resp.status_code == 400


def test_deactivated_account_is_locked_out(client, auth):
    assert client.post("/api/v1/users/deactivate", headers=auth).status_code == 200
    assert client.get("/api/v1/users/me", headers=auth).status_code == 401
    resp = client.post("/api/v1/auth/login", data={"username": "owner@example.com", "password": PASSWORD})
    assert resp.status_code == 401


def test_admin_route_requires_superuser(client, auth):
    assert client.get("/api/v1/admin/users", headers=auth).status_code == 403
    assert client.get("/api/v1/admin/users").status_code == 401
    with SessionLocal() as db:
        db.scalar(select(User).where(User.email == "owner@example.com")).is_superuser = True
        db.commit()
    resp = client.get("/api/v1/admin/users", headers=auth)
    assert resp.status_code == 200
    assert resp.json()[0]["email"] == "owner@example.com"


def test_security_headers_and_request_id(client):
    resp = client.get("/health", headers={"X-Request-ID": "trace-12345678"})
    assert resp.headers["x-request-id"] == "trace-12345678"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert "default-src 'none'" in resp.headers["content-security-policy"]
    assert client.get("/health", headers={"X-Request-ID": "bad\nid"}).headers["x-request-id"] != "bad\nid"


def test_docs_disabled_unknown_host_and_large_body(client):
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/health", headers={"Host": "evil.example"}).status_code == 400
    resp = client.post("/api/v1/auth/register", content=b"x" * 1_100_000, headers={"Content-Type": "application/json"})
    assert resp.status_code == 413


def test_cors_allow_list(client):
    preflight = {"Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "authorization"}
    ok = client.options("/api/v1/accounts", headers={"Origin": "https://app.example.com", **preflight})
    assert ok.headers["access-control-allow-origin"] == "https://app.example.com"
    bad = client.options("/api/v1/accounts", headers={"Origin": "https://evil.example", **preflight})
    assert "access-control-allow-origin" not in bad.headers


def test_ready_checks_database(client):
    assert client.get("/ready").json() == {"status": "Ready", "database": "ok"}


@pytest.mark.parametrize(
    "overrides",
    [{"SECRET_KEY": "short"}, {"SECRET_KEY": "change-me-" + "x" * 40}, {"CORS_ORIGINS": "*"}],
    ids=["short-secret", "placeholder-secret", "wildcard-cors"],
)
def test_insecure_settings_refused(overrides):
    values = {"SECRET_KEY": "k" * 48, "DATABASE_URL": "sqlite://", **overrides}
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


def test_legacy_database_url_uses_psycopg3():
    s = Settings(_env_file=None, SECRET_KEY="k" * 48, DATABASE_URL="postgresql://u:p@db:5432/app")
    assert s.DATABASE_URL.get_secret_value().startswith("postgresql+psycopg://")


def test_xss_payloads_rejected_in_profile(client):
    register_resp = client.post(
        "/api/v1/auth/register",
        json={"full_name": "<script>alert(1)</script>", "email": "x@example.com", "password": PASSWORD},
    )
    assert register_resp.status_code == 422
    register(client, "safe@example.com")
