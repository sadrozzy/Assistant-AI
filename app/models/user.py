from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
from app.models.base import Base


class User(Base):
    telegram_id: Mapped[int] = mapped_column(unique=True, index=True)
    name: Mapped[Optional[str]]
    email: Mapped[Optional[str]]

    google_access_token: Mapped[Optional[str]] = mapped_column(nullable=True)
    google_refresh_token: Mapped[Optional[str]] = mapped_column(nullable=True)
    google_token_expiry: Mapped[Optional[str]] = mapped_column(nullable=True)

    tasks: Mapped[List["Task"]] = relationship(back_populates="user") # type: ignore
    events: Mapped[List["Event"]] = relationship(back_populates="user") # type: ignore
