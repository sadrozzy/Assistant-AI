from aiogram import Router, types
from aiogram.filters import Command
from app.db.repositories.task_repo import TaskRepository
from app.db.session import get_session
from app.schemas.task import TaskCreate
from app.services.calendar import GoogleCalendarService
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
import datetime as dt
from app.utils.logger import logger
from app.db.repositories.user_repo import UserRepository

router = Router()
logger = logger("tasks-handler")


@router.message(Command("newtask"))
async def new_task_handler(message: Message, state: FSMContext):
    try:
        if not message.text:
            await message.answer("Пожалуйста, укажите описание задачи после команды.")
            return
        # Получаем аргументы после команды
        parts = message.text.split(maxsplit=1)
        args = parts[1] if len(parts) > 1 else None
        if not args:
            await message.answer("Пожалуйста, укажите описание задачи после команды.")
            return
        # TODO: Парсинг даты/времени из текста (можно использовать dateparser)
        # Пока только описание
        task_in = TaskCreate(description=args)
        async for session in get_session():
            if not message.from_user:
                await message.answer(
                    "Ошибка: не удалось определить пользователя Telegram."
                )
                return
            user_repo = UserRepository(session)
            user = await user_repo.get_or_create_user(
                telegram_id=message.from_user.id,
                name=message.from_user.full_name or None,
            )
            repo = TaskRepository(session)
            task = await repo.create_task(user_id=user.id, task_in=task_in)
            logger.debug(f"Task added for user {user.id}: {task.description}")
            # TODO: Создать событие в Google Calendar через сервис
            await message.answer(f"Задача добавлена: {task.description}")
    except Exception as e:
        logger.exception(f"Error in new_task_handler: {e}")


@router.message(Command("tasks"))
async def show_tasks_handler(message: Message, state: FSMContext):
    try:
        async for session in get_session():
            if not message.from_user:
                await message.answer(
                    "Ошибка: не удалось определить пользователя Telegram."
                )
                return
            user_repo = UserRepository(session)
            user = await user_repo.get_or_create_user(
                telegram_id=message.from_user.id,
                name=message.from_user.full_name or None,
            )
            repo = TaskRepository(session)
            tasks = await repo.get_tasks_by_user(user_id=user.id)
            if not tasks:
                await message.answer("У вас нет задач.")
                logger.debug(f"User {user.id} has no tasks.")
                return
            text = "\n".join([f"{t.id}. {t.description} ({t.status})" for t in tasks])
            logger.debug(f"User {user.id} tasks listed.")
            await message.answer(f"Ваши задачи:\n{text}")
    except Exception as e:
        logger.exception(f"Error in show_tasks_handler: {e}")


@router.message(Command("deltask"))
async def delete_task_handler(message: Message, state: FSMContext):
    try:
        if not message.text:
            await message.answer("Пожалуйста, укажите id задачи после команды.")
            return
        parts = message.text.split(maxsplit=1)
        arg = parts[1] if len(parts) > 1 else None
        if not arg or not arg.isdigit():
            await message.answer("Пожалуйста, укажите id задачи (например: /deltask 3)")
            return
        task_id = int(arg)
        async for session in get_session():
            if not message.from_user:
                await message.answer(
                    "Ошибка: не удалось определить пользователя Telegram."
                )
                return
            user_repo = UserRepository(session)
            user = await user_repo.get_or_create_user(
                telegram_id=message.from_user.id,
                name=message.from_user.full_name or None,
            )
            repo = TaskRepository(session)
            task = await repo.get_task(task_id)
            if not task or task.user_id != user.id:
                await message.answer("Задача не найдена или не принадлежит вам.")
                return
            await repo.delete_task(task_id)
            logger.debug(f"Task {task_id} deleted for user {user.id}")
            await message.answer(f"Задача {task_id} удалена.")
    except Exception as e:
        logger.exception(f"Error in delete_task_handler: {e}")
