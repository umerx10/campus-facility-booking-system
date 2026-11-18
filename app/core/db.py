"""Database engine, sessions and the SQLite thread-safety strategy (M1 section 7).

Thread-safety strategy: every engine built by `make_engine` applies the SQLAlchemy pysqlite
recipe ("Serializable isolation / Savepoints / Transactional DDL"). The sqlite3 driver normally
delays BEGIN until the first write, so two requests could both read "slot is free" and then both
write. The recipe turns that off (`isolation_level = None`) and issues `BEGIN IMMEDIATE` whenever
SQLAlchemy begins a transaction. `BEGIN IMMEDIATE` takes SQLite's write lock before the transaction
reads anything, so an overlap check and the write that confirms a booking cannot interleave with
another writer. A second writer waits up to `busy_timeout` (5 s) for the lock instead of failing.
"""

import os
from collections.abc import Iterator
from typing import Any

from sqlalchemy import Connection, Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DEFAULT_DATABASE_URL = "sqlite:///cfbs.db"
BUSY_TIMEOUT_MS = 5000


class Base(DeclarativeBase):
    """Declarative base class for every CFBS model. Datetime columns hold naive UTC values."""


def _on_connect(dbapi_connection: Any, _connection_record: Any) -> None:
    """Hand transaction control to SQLAlchemy and enable foreign keys and the lock wait."""
    dbapi_connection.isolation_level = None
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    cursor.close()


def _on_begin(conn: Connection) -> None:
    """Start every transaction by taking the write lock (see the module docstring)."""
    conn.exec_driver_sql("BEGIN IMMEDIATE")


def make_engine(url: str, **kwargs: Any) -> Engine:
    """Create a SQLite engine with the BEGIN IMMEDIATE recipe applied.

    `check_same_thread=False` lets a connection be used by FastAPI's worker threads; safety comes
    from the write lock, not from pinning a connection to one thread.
    """
    connect_args = dict(kwargs.pop("connect_args", {}))
    connect_args.setdefault("check_same_thread", False)
    new_engine = create_engine(url, connect_args=connect_args, **kwargs)
    event.listen(new_engine, "connect", _on_connect)
    event.listen(new_engine, "begin", _on_begin)
    return new_engine


engine = make_engine(os.environ.get("CFBS_DATABASE_URL", DEFAULT_DATABASE_URL))
session_factory = sessionmaker(bind=engine)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed afterwards."""
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
