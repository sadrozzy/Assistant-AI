from aiogram import Router, types
from aiogram.filters import Command
from app.db.repositories.task_repo import TaskRepository
from app.db.session import get_session
from app.schemas.task import TaskCreate
from app.services.calendar import GoogleCalendarService
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import datetime as dt
from app.utils.logger import logger
from app.db.repositories.user_repo import UserRepository
from app.services.google_auth import build_credentials
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest

router = Router()
logger = logger("tasks-handler")


class TaskStates(StatesGroup):
    waiting_for_description = State()

@router.message(Command("newtask"))
async def new_task_handler(message: Message, state: FSMContext):
    try:
        if not message.text:
            await message.answer("Пожалуйста, укажите описание задачи после команды.")
            return
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
            # Получаем credentials пользователя из профиля
            credentials = None
            if user.google_access_token and user.google_refresh_token and user.google_token_expiry:
                expiry = user.google_token_expiry
                if isinstance(expiry, str):
                    try:
                        expiry = dt.datetime.fromisoformat(expiry)
                    except Exception as e:
                        logger.error(f'Ошибка преобразования expiry: {e}')
                logger.debug(f'Google credentials: access_token={user.google_access_token[:6]}..., refresh_token={user.google_refresh_token[:6]}..., expiry={expiry}')
                credentials = build_credentials(
                    access_token=user.google_access_token,
                    refresh_token=user.google_refresh_token,
                    expiry=expiry,
                )
            else:
                await message.answer("Для синхронизации с Google Календарём сначала выполните /googleauth и следуйте инструкции.")
            # Интеграция с Google Calendar
            if credentials:
                try:
                    calendar_service = GoogleCalendarService(credentials)
                    google_event_id = await calendar_service.create_event(
                        user_id=user.id,
                        description=task.description,
                        start=dt.datetime.now(),  # или дату из task_in
                        end=None
                    )
                    await repo.update_task_google_event_id(task.id, google_event_id)
                except Exception as e:
                    logger.exception(f"Ошибка при создании события в Google Calendar: {e}")
                    await message.answer("Ошибка при создании события в Google Календаре. Проверьте авторизацию.")
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


@router.callback_query(lambda c: c.data == "show_tasks")
async def show_tasks_inline_handler(callback: CallbackQuery, state: FSMContext):
    try:
        async for session in get_session():
            if not callback.from_user:
                await callback.message.answer(
                    "Ошибка: не удалось определить пользователя Telegram."
                )
                return
            user_repo = UserRepository(session)
            user = await user_repo.get_or_create_user(
                telegram_id=callback.from_user.id,
                name=callback.from_user.full_name or None,
            )
            repo = TaskRepository(session)
            tasks = await repo.get_tasks_by_user(user_id=user.id)
            if not tasks:
                try:
                    await callback.message.edit_text("У вас нет задач.")
                except TelegramBadRequest:
                    await callback.message.answer("У вас нет задач.")
                logger.debug(f"User {user.id} has no tasks.")
                return
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=f"❌ {t.description}", callback_data=f"delete_task_{t.id}")] for t in tasks
                ]
            )
            try:
                await callback.message.edit_text(
                    "Ваши задачи:",
                    reply_markup=keyboard
                )
            except TelegramBadRequest:
                await callback.message.answer(
                    "Ваши задачи:",
                    reply_markup=keyboard
                )
    except Exception as e:
        logger.exception(f"Error in show_tasks_inline_handler: {e}")


@router.callback_query(lambda c: c.data == "create_task")
async def create_task_inline_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Пожалуйста, введите описание задачи одним сообщением:")
    await state.set_state(TaskStates.waiting_for_description)

@router.message(TaskStates.waiting_for_description)
async def process_task_description(message: Message, state: FSMContext):
    try:
        description = message.text.strip()
        if not description:
            await message.answer("Описание задачи не может быть пустым. Попробуйте ещё раз:")
            return
        async for session in get_session():
            if not message.from_user:
                await message.answer(
                    "Ошибка: не удалось определить пользователя Telegram.")
                return
            user_repo = UserRepository(session)
            user = await user_repo.get_or_create_user(
                telegram_id=message.from_user.id,
                name=message.from_user.full_name or None,
            )
            repo = TaskRepository(session)
            task = await repo.create_task(user_id=user.id, task_in=TaskCreate(description=description))
            logger.debug(f"Task added for user {user.id}: {task.description}")
            # Интеграция с Google Calendar
            credentials = None
            if user.google_access_token and user.google_refresh_token and user.google_token_expiry:
                expiry = user.google_token_expiry
                if isinstance(expiry, str):
                    try:
                        expiry = dt.datetime.fromisoformat(expiry)
                    except Exception as e:
                        logger.error(f'Ошибка преобразования expiry: {e}')
                logger.debug(f'Google credentials: access_token={user.google_access_token[:6]}..., refresh_token={user.google_refresh_token[:6]}..., expiry={expiry}')
                credentials = build_credentials(
                    access_token=user.google_access_token,
                    refresh_token=user.google_refresh_token,
                    expiry=expiry,
                )
            if credentials:
                try:
                    calendar_service = GoogleCalendarService(credentials)
                    google_event_id = await calendar_service.create_event(
                        user_id=user.id,
                        description=task.description,
                        start=dt.datetime.now(),
                        end=None
                    )
                    await repo.update_task_google_event_id(task.id, google_event_id)
                except Exception as e:
                    logger.exception(f"Ошибка при создании события в Google Calendar: {e}")
                    await message.answer("Ошибка при создании события в Google Календаре. Проверьте авторизацию.")
            await message.answer(f"Задача добавлена: {task.description}")
        await state.clear()
        # Показываем обновлённый список задач через inline-меню
        # Имитация callback для show_tasks
        fake_callback = type('FakeCallback', (), {'from_user': message.from_user, 'message': message})
        await show_tasks_inline_handler(fake_callback, state)
    except Exception as e:
        logger.exception(f"Error in process_task_description: {e}")


@router.callback_query(lambda c: c.data.startswith("delete_task_"))
async def delete_task_inline_handler(callback: CallbackQuery, state: FSMContext):
    try:
        task_id = int(callback.data.split("delete_task_")[1])
        async for session in get_session():
            if not callback.from_user:
                await callback.message.answer(
                    "Ошибка: не удалось определить пользователя Telegram."
                )
                return
            user_repo = UserRepository(session)
            user = await user_repo.get_or_create_user(
                telegram_id=callback.from_user.id,
                name=callback.from_user.full_name or None,
            )
            repo = TaskRepository(session)
            task = await repo.get_task(task_id)
            if not task or task.user_id != user.id:
                await callback.answer("Задача не найдена или не принадлежит вам.", show_alert=True)
                return
            await repo.delete_task(task_id)
            logger.debug(f"Task {task_id} deleted for user {user.id}")
            # Удаление события из Google Calendar
            credentials = None
            if user.google_access_token and user.google_refresh_token and user.google_token_expiry:
                expiry = user.google_token_expiry
                if isinstance(expiry, str):
                    try:
                        expiry = dt.datetime.fromisoformat(expiry)
                    except Exception as e:
                        logger.error(f'Ошибка преобразования expiry: {e}')
                logger.debug(f'Google credentials: access_token={user.google_access_token[:6]}..., refresh_token={user.google_refresh_token[:6]}..., expiry={expiry}')
                credentials = build_credentials(
                    access_token=user.google_access_token,
                    refresh_token=user.google_refresh_token,
                    expiry=expiry,
                )
            if credentials and task.google_event_id:
                try:
                    calendar_service = GoogleCalendarService(credentials)
                    await calendar_service.delete_event(task.google_event_id)
                except Exception as e:
                    logger.exception(f"Ошибка при удалении события из Google Calendar: {e}")
                    await callback.message.answer("Ошибка при удалении события из Google Календаря. Проверьте авторизацию.")
            await callback.answer("Задача удалена!", show_alert=True)
            # Обновляем список задач
            # Повторно вызываем show_tasks_inline_handler
            await show_tasks_inline_handler(callback, state)
    except Exception as e:
        logger.exception(f"Error in delete_task_inline_handler: {e}")
