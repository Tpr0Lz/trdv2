from __future__ import annotations

import os
from urllib.parse import urlparse

import pytest
from sqlalchemy import create_engine, text

from app.core.config import get_settings
from app.db.base import Base
from app.db import models  # noqa: F401
from app.db.session import reconfigure_session_factory

TEST_DATABASE_URL = "postgresql+psycopg://tradingagents:tradingagents@localhost:54329/tradingagents_v2_test"


def _admin_database_url(database_url: str) -> str:
    parsed = urlparse(database_url)
    database_name = parsed.path.rsplit("/", 1)[-1]
    admin_path = parsed.path[: -len(database_name)] + "postgres"
    return parsed._replace(path=admin_path).geturl()


def _database_name(database_url: str) -> str:
    return urlparse(database_url).path.rsplit("/", 1)[-1]


def _assert_test_database(database_url: str) -> None:
    database_name = _database_name(database_url)
    if not database_name.endswith("_test"):
        raise RuntimeError(f"Refusing to reset non-test database: {database_name}")


def _ensure_test_database(database_url: str) -> None:
    admin_engine = create_engine(_admin_database_url(database_url), isolation_level="AUTOCOMMIT")
    database_name = _database_name(database_url)
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :database_name"),
            {"database_name": database_name},
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{database_name}"'))
    admin_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def isolate_test_database() -> None:
    # 中文注释：pytest 会话统一切到独立测试库，避免清空本地开发 runs 历史。
    os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", TEST_DATABASE_URL)
    get_settings.cache_clear()
    database_url = get_settings().database_url
    _assert_test_database(database_url)
    _ensure_test_database(database_url)
    reconfigure_session_factory(database_url)

    from app.db.session import engine

    # 中文注释：测试库每次按模型重建，避免旧 schema 缺新列导致测试误失败。
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
