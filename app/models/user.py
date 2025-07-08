from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
from app.models.base import Base


class User(Base):
    telegram_id: Mapped[int] = mapped_column(unique=True, index=True)
    name: Mapped[Optional[str]]
    email: Mapped[Optional[str]]

    tasks: Mapped[List["Task"]] = relationship(back_populates="user") # type: ignore
    events: Mapped[List["Event"]] = relationship(back_populates="user") # type: ignore
