from pydantic import BaseModel
from typing import Optional
import datetime as dt


class TaskBase(BaseModel):
    description: str
    datetime: Optional[dt.datetime] = None
    remind_at: Optional[int] = None  
    status: Optional[str] = "pending"
    google_event_id: Optional[str] = None
    duration: Optional[int] = None  


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    description: Optional[str] = None
    datetime: Optional[dt.datetime] = None
    remind_at: Optional[int] = None
    status: Optional[str] = None
    google_event_id: Optional[str] = None
    duration: Optional[int] = None


class TaskOut(TaskBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True
