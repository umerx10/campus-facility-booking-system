"""Shared pytest fixtures for every CFBS module.

Changes to this file go through a pull request reviewed by the M2 SE423 lead (see
docs/architecture-contract.md).

Fixtures:
    engine               in-memory SQLite, one shared connection (StaticPool), all tables created.
    db_session           a Session on that engine, closed after the test.
    client               a TestClient whose requests use db_session instead of the app database.
    as_user              as_user(role, user_id=1) makes every request run as that user.
    file_engine          SQLite on a temporary file, for concurrency and threaded tests.
    session_factory_file a sessionmaker bound to file_engine.
"""

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_session, make_engine
from app.core.deps import CurrentUser, get_current_user
from app.core.enums import Role
from app.main import app


@pytest.fixture
def engine() -> Iterator[Engine]:
    """In-memory database. StaticPool keeps one connection, so every session sees the same tables."""
    test_engine = make_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    """A session on the in-memory engine, closed after the test."""
    session = Session(engine)
    yield session
    session.close()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    """HTTP client for the app, with get_session overridden to yield the test session.

    TestClient is not used as a context manager, so the app's lifespan handler does not run and the
    tests never create or touch the real cfbs.db file.
    """

    def _test_session() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_session] = _test_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def as_user() -> Iterator[Callable[..., CurrentUser]]:
    """Return as_user(role, user_id=1); after calling it, requests run as that user."""

    def _as_user(role: Role, user_id: int = 1) -> CurrentUser:
        user = CurrentUser(id=user_id, role=role)
        app.dependency_overrides[get_current_user] = lambda: user
        return user

    yield _as_user
    app.dependency_overrides.clear()


@pytest.fixture
def file_engine(tmp_path: Path) -> Iterator[Engine]:
    """SQLite on a temporary file, so several connections really compete for the write lock."""
    db_file = tmp_path / "cfbs-test.db"
    test_engine = make_engine(f"sqlite:///{db_file.as_posix()}")
    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def session_factory_file(file_engine: Engine) -> sessionmaker[Session]:
    """Session factory on the file database, for code that opens its own sessions (worker threads)."""
    return sessionmaker(bind=file_engine)
