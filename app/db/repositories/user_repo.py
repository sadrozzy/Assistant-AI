from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import User
from typing import Optional


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_user(
        self, telegram_id: int, name: Optional[str] = None, email: Optional[str] = None
    ) -> User:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalars().first()
        if user:
            return user
        user = User(telegram_id=telegram_id, name=name, email=email)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
