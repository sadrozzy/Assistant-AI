from pydantic import BaseModel
from typing import Optional


class UserCreate(BaseModel):
    telegram_id: int
    name: Optional[str] = None
    email: Optional[str] = None
