from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.db.repositories.task_repo import TaskRepository
from app.services.calendar import GoogleCalendarService
from typing import List

router = APIRouter()


@router.get("/calendar/sync")
async def sync_calendar(user_id: int, session: AsyncSession = Depends(get_session)):
    repo = TaskRepository(session)
    tasks = await repo.get_tasks_by_user(user_id)
    # TODO: Получить credentials пользователя
    calendar_service = GoogleCalendarService(credentials=None)
    synced = []
    for task in tasks:
        if not task.google_event_id and task.due_datetime:
            # Пример синхронизации: создаём событие в календаре
            event_id = await calendar_service.create_event(
                user_id=user_id, description=task.description, start=task.due_datetime
            )
            # Можно обновить задачу с google_event_id
            synced.append({"task_id": task.id, "event_id": event_id})
    return {"synced": synced}
