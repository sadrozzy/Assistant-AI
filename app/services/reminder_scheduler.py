import asyncio
import datetime as dt
from app.db.session import get_session
from app.db.repositories.task_repo import TaskRepository
from app.db.repositories.user_repo import UserRepository
from aiogram import Bot
from aiogram.types import Message

CHECK_INTERVAL = 60  # секунд между проверками

async def reminder_scheduler(bot: Bot):
    while True:
        now = dt.datetime.now()
        async for session in get_session():
            repo = TaskRepository(session)
            user_repo = UserRepository(session)
            # Получаем задачи, у которых remind_at <= сейчас и статус не "reminded"
            tasks = await repo.get_tasks_to_remind(now)
            for task in tasks:
                user = await user_repo.get_user_by_id(task.user_id)
                if user and user.telegram_id:
                    try:
                        await bot.send_message(user.telegram_id, f"⏰ Напоминание: {task.description}")
                        await repo.mark_task_reminded(task.id)
                    except Exception as e:
                        print(f"Ошибка отправки напоминания: {e}")
        await asyncio.sleep(CHECK_INTERVAL)

# Для запуска планировщика в main.py:
# from app.services.reminder_scheduler import reminder_scheduler
# asyncio.create_task(reminder_scheduler(bot)) 