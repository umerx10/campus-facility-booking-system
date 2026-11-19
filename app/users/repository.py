"""Database access for users. All user SQL lives here."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.users.models import User


class UserRepository:
    """Reads and adds users through the session it is given; it never commits on its own."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_email(self, email: str) -> User | None:
        """Return the user with this email, or None."""
        return self._session.scalar(select(User).where(User.email == email))

    def get_by_id(self, user_id: int) -> User | None:
        """Return the user with this id, or None."""
        return self._session.get(User, user_id)

    def list_all(self) -> list[User]:
        """Return every user, ordered by id."""
        return list(self._session.scalars(select(User).order_by(User.id)))

    def add(self, user: User) -> User:
        """Stage a new user and flush so it gets an id; the caller commits."""
        self._session.add(user)
        self._session.flush()
        return user
