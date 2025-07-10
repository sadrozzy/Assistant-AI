from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from typing import Optional
from app.models.base import Base


class Task(Base):
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    status: Mapped[str] = mapped_column(default="pending")

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    description: Mapped[str]

    due_datetime: Mapped[Optional[str]]
    remind_at: Mapped[Optional[int]] 
    duration: Mapped[Optional[int]]  

    isReminded: Mapped[bool] = mapped_column(default=False)  
    google_event_id: Mapped[Optional[str]]

    user = relationship("User", back_populates="tasks")
