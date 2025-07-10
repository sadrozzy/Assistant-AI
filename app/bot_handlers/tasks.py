from aiogram import Router, types
from aiogram.filters import Command, CommandObject, CommandStart
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
import re
from typing import Optional

from app.utils import parse_task_text
from app.services.sync_google_calendar import sync_task_with_google_calendar

router = Router()
logger = logger("tasks-handler")


class TaskStates(StatesGroup):
    waiting_for_description = State()

def ensure_datetime(dt_value):
    if isinstance(dt_value, str):
        return dt.datetime.fromisoformat(dt_value)
    return dt_value

def calc_remind_at(due_datetime, reminder):
    if not due_datetime or reminder is None:
        return None
    if isinstance(reminder, int):
        # reminder уже в минутах
        return due_datetime - dt.timedelta(minutes=reminder)
    if isinstance(reminder, str):
        match = re.match(r'(\d+)([мчдmhd])', reminder, re.IGNORECASE)
        if not match:
            return None
        value, unit = int(match.group(1)), match.group(2).lower()
        if unit in ['м', 'm']:
            delta = dt.timedelta(minutes=value)
        elif unit in ['ч', 'h']:
            delta = dt.timedelta(hours=value)
        elif unit in ['д', 'd']:
            delta = dt.timedelta(days=value)
        else:
            return None
        return due_datetime - delta
    return None

# --- Утилита для работы с tzoffset типа '+03:00' ---
def get_tzinfo(tz_str: Optional[str]) -> dt.timezone:
    if not tz_str:
        return dt.timezone(dt.timedelta(hours=3))  # по умолчанию +03:00
    sign = 1 if tz_str.startswith('+') else -1
    hours, minutes = map(int, tz_str[1:].split(':'))
    return dt.timezone(sign * dt.timedelta(hours=hours, minutes=minutes))


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
                        start=dt.datetime.now(), 
                        end=None
                    )
                    await repo.update_task_google_event_id(task.id, google_event_id)
                except Exception as e:
                    logger.exception(f"Ошибка при создании события в Google Calendar: {e}")
                    await message.answer("Ошибка при создании события в Google Календаре. Проверьте авторизацию.")
            sync_ok, sync_msg = await sync_task_with_google_calendar(user, task)
            await message.answer(f"Задача добавлена: {task.description}\n{sync_msg}")
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
                    end_time = None
                    if getattr(task, 'due_datetime', None) and getattr(task, 'duration', None):
                        try:
                            start_dt = ensure_datetime(task.due_datetime)
                            end_time = start_dt + dt.timedelta(minutes=task.duration)
                        except Exception:
                            end_time = None
                    reminder_minutes = None
                    if getattr(task, 'remind_at', None) is not None:
                        try:
                            reminder_minutes = int(task.remind_at)
                        except Exception:
                            reminder_minutes = None
                    logger.info(f"Google Calendar event params: user_id={user.id}, description={task.description}, start={ensure_datetime(task.due_datetime) if getattr(task, 'due_datetime', None) else dt.datetime.now()}, end={end_time}, reminder={reminder_minutes}")
                    google_event_id = await calendar_service.create_event(
                        user_id=user.id,
                        description=task.description,
                        start=ensure_datetime(task.due_datetime) if getattr(task, 'due_datetime', None) else dt.datetime.now(),
                        end=end_time,
                        reminder_minutes=reminder_minutes
                    )
                    await repo.update_task_google_event_id(task.id, google_event_id)
                except Exception as e:
                    logger.exception(f"Ошибка при создании события в Google Calendar: {e}")
                    await message.answer("Ошибка при создании события в Google Календаре. Проверьте авторизацию.")
            sync_ok, sync_msg = await sync_task_with_google_calendar(user, task)
            await message.answer(f"Задача добавлена: {task.description}\n{sync_msg}")
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
            await show_tasks_inline_handler(callback, state)
    except Exception as e:
        logger.exception(f"Error in delete_task_inline_handler: {e}")


@router.message(lambda m: m.chat.type == 'private' and m.text and not m.text.startswith('/'))
async def handle_inbox_or_scheduled_task(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == "waiting_for_google_code":
        return
    if not message.text:
        return
    parsed = parse_task_text(message.text)

    async for session in get_session():
        if not message.from_user:
            await message.answer("Ошибка: не удалось определить пользователя Telegram.")
            return
        user_repo = UserRepository(session)
        user = await user_repo.get_or_create_user(
            telegram_id=message.from_user.id,
            name=message.from_user.full_name or None,
        )
        user_tz = get_tzinfo(getattr(user, 'timezone', None))
        now = dt.datetime.now(dt.timezone.utc)
        now_local = now.astimezone(user_tz)
        # --- Вычисление абсолютной даты/времени задачи ---
        task_datetime = None
        if parsed['time'] and not parsed['date']:
            h, m = map(int, re.split(r'[:\-]', parsed['time']))
            task_dt = now_local.replace(hour=h, minute=m, second=0, microsecond=0)
            if task_dt < now_local:
                task_dt = task_dt + dt.timedelta(days=1)
            task_datetime = task_dt.astimezone(dt.timezone.utc)
        elif parsed['date']:
            # Можно добавить обработку даты + времени, если нужно
            pass
        status = 'inbox'
        if parsed['date'] or parsed['time']:
            status = 'scheduled'
        remind_at = None
        if task_datetime and parsed['reminder']:
            remind_at = calc_remind_at(task_datetime, parsed['reminder'])
        task_in = TaskCreate(
            description=parsed['clean_text'],
            datetime=task_datetime.isoformat() if task_datetime else None,
            remind_at=parsed['reminder'],  # теперь это int минут
            status=status,
            duration=parsed['duration']  # теперь это int минут
        )
        repo = TaskRepository(session)
        task = await repo.create_task(user_id=user.id, task_in=task_in)
        sync_ok, sync_msg = await sync_task_with_google_calendar(user, task, parsed)
        if status == 'inbox':
            await message.answer(f'Задача добавлена в Инбокс: {task.description}\n{sync_msg}')
        else:
            # Формируем подробное сообщение о задаче
            details = []
            if getattr(task, 'remind_at', None):
                details.append(f'⏰ Напоминание: за {task.remind_at} минут')
            if getattr(task, 'duration', None):
                details.append(f'⏳ Длительность: {task.duration} минут')
            if getattr(task, 'due_datetime', None):
                try:
                    due_dt = dt.datetime.fromisoformat(task.due_datetime)
                    due_local = due_dt.astimezone(user_tz)
                    details.append(f'📅 Дата и время: {due_local.strftime("%d.%m %H:%M")}')
                except Exception:
                    details.append(f'📅 Дата и время: {task.due_datetime}')
            elif getattr(task, 'date', None):
                details.append(f'📅 Дата: {task.date}')
            elif getattr(task, 'time', None):
                details.append(f'🕒 Время: {task.time}')
            details_text = '\n'.join(details)
            msg = f'Задача запланирована: {task.description}'
            if details_text:
                msg += f'\n{details_text}'
            await message.answer(msg + f"\n{sync_msg}")
            # --- Интеграция с Google Calendar ---
            credentials = None
            if user.google_access_token and user.google_refresh_token and user.google_token_expiry:
                expiry = user.google_token_expiry
                if isinstance(expiry, str):
                    try:
                        expiry = dt.datetime.fromisoformat(expiry)
                    except Exception as e:
                        logger.error(f'Ошибка преобразования expiry: {e}')
                credentials = build_credentials(
                    access_token=user.google_access_token,
                    refresh_token=user.google_refresh_token,
                    expiry=expiry,
                )
            if credentials and task_datetime:
                try:
                    calendar_service = GoogleCalendarService(credentials)
                    end_time = None
                    if getattr(task, 'due_datetime', None) and getattr(task, 'duration', None):
                        try:
                            start_dt = ensure_datetime(task.due_datetime)
                            end_time = start_dt + dt.timedelta(minutes=task.duration)
                        except Exception:
                            end_time = None
                    google_event_id = await calendar_service.create_event(
                        user_id=user.id,
                        description=task.description,
                        start=ensure_datetime(task.due_datetime) if getattr(task, 'due_datetime', None) else dt.datetime.now(),
                        end=end_time
                    )
                    await repo.update_task_google_event_id(task.id, google_event_id)
                    await message.answer("Событие добавлено в Google Calendar.")
                except Exception as e:
                    logger.exception(f"Ошибка при создании события в Google Calendar: {e}")
                    await message.answer("Ошибка при создании события в Google Календаре. Проверьте авторизацию.")
