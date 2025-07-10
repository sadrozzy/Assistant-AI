import datetime as dt
from app.services.calendar import GoogleCalendarService
from app.services.google_auth import build_credentials
from app.db.repositories.task_repo import TaskRepository
from app.db.session import get_session
from app.utils.logger import logger

def get_tzinfo(tz_str):
    if not tz_str:
        return dt.timezone(dt.timedelta(hours=3))
    sign = 1 if str(tz_str).startswith('+') else -1
    hours, minutes = map(int, str(tz_str)[1:].split(':'))
    return dt.timezone(sign * dt.timedelta(hours=hours, minutes=minutes))

async def sync_task_with_google_calendar(user, task, parsed=None):
    """
    Синхронизирует задачу с Google Calendar, если у пользователя есть токены.
    task — объект Task (или словарь с нужными полями)
    parsed — результат parse_task_text (опционально)
    """
    log = logger("sync-google-calendar")
    credentials = None
    if user.google_access_token and user.google_refresh_token and user.google_token_expiry:
        expiry = user.google_token_expiry
        if isinstance(expiry, str):
            try:
                expiry = dt.datetime.fromisoformat(expiry)
            except Exception:
                pass
        credentials = build_credentials(
            access_token=user.google_access_token,
            refresh_token=user.google_refresh_token,
            expiry=expiry,
        )
    if not credentials:
        return False, "Нет авторизации Google. Выполните /google."
    try:
        calendar_service = GoogleCalendarService(credentials)
        # Определяем start, end, reminder
        user_tz = get_tzinfo(getattr(user, 'timezone', None))
        start = None
        end = None
        reminder_minutes = None
        # Если есть due_datetime — используем его
        if getattr(task, 'due_datetime', None):
            start = dt.datetime.fromisoformat(task.due_datetime)
        elif parsed and parsed.get('time') and not parsed.get('date'):
            now = dt.datetime.now(dt.timezone.utc)
            now_local = now.astimezone(user_tz)
            h, m = map(int, str(parsed['time']).replace('-', ':').split(':'))
            task_dt = now_local.replace(hour=h, minute=m, second=0, microsecond=0)
            if task_dt < now_local:
                task_dt = task_dt + dt.timedelta(days=1)
            start = task_dt.astimezone(dt.timezone.utc)
        else:
            start = dt.datetime.now(dt.timezone.utc)
        if getattr(task, 'duration', None):
            end = start + dt.timedelta(minutes=task.duration)
        if getattr(task, 'remind_at', None):
            try:
                reminder_minutes = int(task.remind_at)
            except Exception:
                reminder_minutes = None
        description = getattr(task, 'description', None) or (parsed.get('clean_text') if parsed else None)
        google_event_id = await calendar_service.create_event(
            user_id=user.id,
            description=description,
            start=start,
            end=end,
            reminder_minutes=reminder_minutes
        )
        # Сохраняем google_event_id в задаче
        async for session2 in get_session():
            repo = TaskRepository(session2)
            await repo.update_task_google_event_id(task.id, google_event_id)
            break
        return True, "Событие добавлено в Google Календарь."
    except Exception as e:
        log.exception(f"Ошибка при создании события в Google Calendar: {e}")
        return False, "Ошибка при создании события в Google Календаре. Проверьте авторизацию." 