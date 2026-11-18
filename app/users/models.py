"""User table. Name and password_hash were added to the M1 schema because login needs them."""

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.enums import Role


class User(Base):
    """A person who can sign in. Only a salted hash of the password is stored (QR-04)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False, length=20))
    password_hash: Mapped[str] = mapped_column(String(255))
