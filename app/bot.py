from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from app.bot_handlers import tasks, voice, start, google_connect
import asyncio
from app.config import settings
from app.utils.logger import logger
from app.services.reminder_scheduler import reminder_scheduler


bot = Bot(token=settings.TELEGRAM_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
logger = logger("bot")


def register_handlers():
    dp.include_router(google_connect.router)
    
    dp.include_router(start.router)
    dp.include_router(tasks.router)
    dp.include_router(voice.router)



async def start_bot():
    try:
        register_handlers()
        logger.info("Bot is starting polling...")
        # Запуск планировщика напоминаний
        asyncio.create_task(reminder_scheduler(bot))
        await dp.start_polling(bot)
    except Exception as e:
        logger.exception(f"Bot failed to start: {e}")


if __name__ == "__main__":
    logger.info("Running bot")
    asyncio.run(start_bot())
