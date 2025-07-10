from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.task import Task
from app.schemas.task import TaskCreate
from typing import List, Optional
from app.utils.logger import logger
from sqlalchemy import and_
import datetime as dt
from datetime import datetime, timedelta


class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.log = logger("TaskRepository")

    async def create_task(self, user_id: int, task_in: TaskCreate) -> Task:
        self.log.debug(f"Создание задачи для user_id={user_id}, данные: {task_in}")

        due_dt = task_in.datetime.isoformat() if isinstance(task_in.datetime, dt.datetime) else task_in.datetime
        remind_at = None
        
        if isinstance(task_in.remind_at, dt.datetime):
            remind_at = task_in.remind_at.isoformat()
        else:
            remind_at = task_in.remind_at
        task = Task(
            user_id=user_id,
            description=task_in.description,
            due_datetime=due_dt,
            remind_at=task_in.remind_at,
            status=task_in.status,
            google_event_id=task_in.google_event_id,
            duration=task_in.duration,
            isReminded=False
        )
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        self.log.debug(f"Задача создана: {task}")
        return task

    async def get_tasks_by_user(self, user_id: int) -> List[Task]:
        self.log.debug(f"Получение задач пользователя user_id={user_id}")
        result = await self.session.execute(select(Task).where(Task.user_id == user_id))
        tasks = list(result.scalars().all())
        self.log.debug(f"Найдено задач: {len(tasks)}")
        return tasks

    async def get_task(self, task_id: int) -> Optional[Task]:
        self.log.debug(f"Получение задачи по id={task_id}")
        result = await self.session.execute(select(Task).where(Task.id == task_id))
        task = result.scalars().first()
        self.log.debug(f"Результат: {task}")
        return task

    async def delete_task(self, task_id: int) -> None:
        self.log.debug(f"Удаление задачи id={task_id}")
        task = await self.get_task(task_id)
        if task:
            await self.session.delete(task)
            await self.session.commit()
            self.log.debug(f"Задача удалена: {task_id}")
        else:
            self.log.debug(f"Задача для удаления не найдена: {task_id}")

    async def update_task_google_event_id(self, task_id: str, google_event_id: str) -> None:
        self.log.debug(f"Обновление google_event_id для задачи id={task_id}")
        task = await self.get_task(task_id)
        if task:
            task.google_event_id = google_event_id
            await self.session.commit()
            await self.session.refresh(task)
            self.log.debug(f"google_event_id обновлён для задачи id={task_id}")
        else:
            self.log.debug(f"Задача для обновления google_event_id не найдена: {task_id}")

    @staticmethod
    def _to_utc(dt_str):
        """Преобразует строку ISO в datetime с tzinfo=UTC."""
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(dt_str)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    async def get_tasks_to_remind(self, now) -> List[Task]:
        """
        Возвращает задачи, для которых пора отправить напоминание.
        now — datetime (желательно с tzinfo=UTC)
        """
        from datetime import timedelta, timezone
        self.log.debug(f"Получение задач для напоминания на {now}")
        result = await self.session.execute(
            select(Task).where(
                Task.due_datetime != None,
                Task.remind_at != None,
                Task.isReminded == False
            )
        )
        tasks = list(result.scalars().all())
        now_aware = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
        filtered = []
        for task in tasks:
            try:
                due = self._to_utc(task.due_datetime)
                remind_time = due - timedelta(minutes=int(task.remind_at))
                if remind_time <= now_aware < due:
                    filtered.append(task)
            except Exception as e:
                self.log.debug(f"Ошибка при вычислении времени напоминания для задачи {task.id}: {e}")
        self.log.debug(f"Найдено задач для напоминания: {len(filtered)}")
        return filtered

    async def mark_task_reminded(self, task_id: int) -> None:
        self.log.debug(f"Помечаю задачу как напомненную: id={task_id}")
        task = await self.get_task(task_id)
        if task:
            task.isReminded = True
            await self.session.commit()
            await self.session.refresh(task)
            self.log.debug(f"Задача помечена как напомненная: id={task_id}")