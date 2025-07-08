from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.db.repositories.task_repo import TaskRepository
from app.schemas.task import TaskCreate, TaskOut
from typing import List

router = APIRouter()


@router.get("/tasks/{user_id}", response_model=List[TaskOut])
async def get_tasks(user_id: int, session: AsyncSession = Depends(get_session)):
    repo = TaskRepository(session)
    return await repo.get_tasks_by_user(user_id)


@router.post("/tasks/{user_id}", response_model=TaskOut)
async def create_task(
    user_id: int, task_in: TaskCreate, session: AsyncSession = Depends(get_session)
):
    repo = TaskRepository(session)
    return await repo.create_task(user_id, task_in)


@router.delete("/tasks/{user_id}/{task_id}")
async def delete_task(
    user_id: int, task_id: int, session: AsyncSession = Depends(get_session)
):
    repo = TaskRepository(session)
    task = await repo.get_task(task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(status_code=404, detail="Task not found")
    await repo.delete_task(task_id)
    return {"ok": True}
