from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from app.models.base import Base
from app.models.user import User
from sqlalchemy import ForeignKey


class Event(Base):
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str]
    description: Mapped[Optional[str]]
    start_datetime: Mapped[str]
    end_datetime: Mapped[str]
    google_event_id: Mapped[Optional[str]]

    user: Mapped["User"] = relationship(back_populates="events")
