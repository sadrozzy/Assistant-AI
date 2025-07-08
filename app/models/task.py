from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from typing import Optional
from app.models.base import Base


class Task(Base):
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    description: Mapped[str]
    due_datetime: Mapped[Optional[str]]
    status: Mapped[str] = mapped_column(default="pending")
    google_event_id: Mapped[Optional[str]]

    user = relationship("User", back_populates="tasks")
