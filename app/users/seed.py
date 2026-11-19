"""Create the three demo users. Run with: python -m app.users.seed

Safe to run repeatedly: a user is created only if its email is missing. The passwords are
development passwords for the local demo only; they are printed when the user is created.
"""

from sqlalchemy.orm import Session

from app.core.db import engine, session_factory
from app.core.enums import Role
from app.models_registry import create_all_tables
from app.users.models import User
from app.users.repository import UserRepository
from app.users.security import hash_password

# (name, email, role, development password)
DEMO_USERS: tuple[tuple[str, str, Role, str], ...] = (
    ("Demo Admin", "admin@cfbs.local", Role.ADMIN, "admin-dev-pass"),
    ("Demo Faculty", "faculty@cfbs.local", Role.FACULTY, "faculty-dev-pass"),
    ("Demo Student", "student@cfbs.local", Role.STUDENT, "student-dev-pass"),
)


def seed_demo_users(session: Session) -> list[str]:
    """Create any missing demo users, commit, and return the emails that were created."""
    users = UserRepository(session)
    created: list[str] = []
    for name, email, role, password in DEMO_USERS:
        if users.get_by_email(email) is None:
            users.add(
                User(name=name, email=email, role=role, password_hash=hash_password(password))
            )
            created.append(email)
    session.commit()
    return created


def main() -> None:
    """Create tables if needed, seed, and print what was created."""
    create_all_tables(engine)
    with session_factory() as session:
        created = seed_demo_users(session)
    if not created:
        print("Demo users already exist; nothing created.")
    for _, email, role, password in DEMO_USERS:
        if email in created:
            print(f"Created {role.value:<8} {email}  password: {password}")


if __name__ == "__main__":
    main()
