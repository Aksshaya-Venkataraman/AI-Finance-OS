"""Runs the full Alembic history against a real PostgreSQL database.

Skipped unless TEST_POSTGRES_URL points at an empty, disposable database
(CI provides one). The original migrations use PostgreSQL-only DDL, so they
cannot be checked on SQLite.
"""

import os
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from alembic import command
from backend.app.database.init_db import Base

URL = os.environ.get("TEST_POSTGRES_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_POSTGRES_URL not set")
ROOT = Path(__file__).resolve().parents[1]


def test_migrations_upgrade_downgrade_and_match_models(monkeypatch):
    from backend.app.core import config

    monkeypatch.setattr(config.settings, "DATABASE_URL", config.Settings._psycopg3_driver(config.SecretStr(URL)))
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))

    command.upgrade(cfg, "head")
    engine = create_engine(config.settings.DATABASE_URL.get_secret_value())
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert diff == []

    command.downgrade(cfg, "d3c649f0e4b0")
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    engine.dispose()
