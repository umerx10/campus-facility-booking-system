"""Tests for the demo-user seed script (python -m app.users.seed)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import Role
from app.users.models import User
from app.users.seed import seed_demo_users

DEMO_EMAILS = ["admin@cfbs.local", "faculty@cfbs.local", "student@cfbs.local"]


def test_seed_creates_one_demo_user_per_role(db_session: Session) -> None:
    created = seed_demo_users(db_session)

    users = db_session.scalars(select(User)).all()
    assert sorted(created) == DEMO_EMAILS
    assert sorted(user.email for user in users) == DEMO_EMAILS
    assert {user.role for user in users} == {Role.ADMIN, Role.FACULTY, Role.STUDENT}


def test_running_the_seed_twice_adds_nothing_the_second_time(db_session: Session) -> None:
    seed_demo_users(db_session)

    created_again = seed_demo_users(db_session)

    users = db_session.scalars(select(User)).all()
    assert created_again == []
    assert sorted(user.email for user in users) == DEMO_EMAILS
