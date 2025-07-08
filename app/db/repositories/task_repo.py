from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.task import Task
from app.schemas.task import TaskCreate
from typing import List, Optional


class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_task(self, user_id: int, task_in: TaskCreate) -> Task:
        task = Task(
            user_id=user_id,
            description=task_in.description,
            due_datetime=task_in.datetime,
            status=task_in.status,
            google_event_id=task_in.google_event_id,
        )
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def get_tasks_by_user(self, user_id: int) -> List[Task]:
        result = await self.session.execute(select(Task).where(Task.user_id == user_id))
        return list(result.scalars().all())

    async def get_task(self, task_id: int) -> Optional[Task]:
        result = await self.session.execute(select(Task).where(Task.id == task_id))
        return result.scalars().first()

    async def delete_task(self, task_id: int) -> None:
        task = await self.get_task(task_id)
        if task:
            await self.session.delete(task)
            await self.session.commit()
