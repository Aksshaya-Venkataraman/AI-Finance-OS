"""Test configuration: in-memory SQLite, generated secrets, fresh tables per test."""

import os
import secrets

# Must be set before the application modules are imported.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", secrets.token_urlsafe(48))
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("ALLOWED_HOSTS", "testserver")
os.environ.setdefault("CORS_ORIGINS", "https://app.example.com")
os.environ.setdefault("LOGIN_RATE_LIMIT", "100/minute")
os.environ.setdefault("REGISTER_RATE_LIMIT", "100/minute")
os.environ.setdefault("PASSWORD_RESET_RATE_LIMIT", "100/minute")
os.environ.setdefault("ASSISTANT_RATE_LIMIT", "100/minute")

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from backend.app.core.rate_limit import reset_limits
from backend.app.database.init_db import Base
from backend.app.database.session import engine
from backend.app.main import app

PASSWORD = "correct-horse-battery-staple"


@pytest.fixture(autouse=True)
def fresh_database() -> Iterator[None]:
    Base.metadata.create_all(engine)
    reset_limits()
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def register(client: TestClient, email: str, password: str = PASSWORD, name: str = "Test User") -> dict:
    resp = client.post("/api/v1/auth/register", json={"full_name": name, "email": email, "password": password})
    assert resp.status_code == 201, resp.text
    return resp.json()


def login(client: TestClient, email: str, password: str = PASSWORD) -> dict[str, str]:
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def auth(client: TestClient) -> dict[str, str]:
    register(client, "owner@example.com")
    return login(client, "owner@example.com")


@pytest.fixture
def other_auth(client: TestClient) -> dict[str, str]:
    register(client, "intruder@example.com")
    return login(client, "intruder@example.com")
