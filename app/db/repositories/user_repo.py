from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import User
from typing import Optional
from app.utils.logger import logger


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.log = logger("UserRepository")

    async def get_or_create_user(
        self, telegram_id: int, name: Optional[str] = None
    ) -> User:
        self.log.debug(f"Поиск пользователя telegram_id={telegram_id}")
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalars().first()
        if user:
            self.log.debug(f"Пользователь найден: {user}")
            return user
        self.log.debug(f"Пользователь не найден, создаю нового: telegram_id={telegram_id}, name={name}")
        user = User(telegram_id=telegram_id, name=name)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        self.log.debug(f"Пользователь создан: {user}")
        return user
