from pydantic import BaseModel
from typing import Optional


class UserBase(BaseModel):
    telegram_id: int
    name: Optional[str] = None
    timezone: Optional[str] = "+03:00"


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    name: Optional[str] = None
    timezone: Optional[str] = None


class UserOut(UserBase):
    id: int
    class Config:
        from_attributes = True
