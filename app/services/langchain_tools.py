from langchain.tools import BaseTool
from app.db.session import get_session
from app.db.repositories.task_repo import TaskRepository
from app.schemas.task import TaskCreate
from typing import Optional, Any, Type

class AddTaskTool(BaseTool):
    name: str = "add_task"
    description: str = "Добавить новую задачу пользователю. Обязательные параметры: user_id (int), description (str)."
    args_schema: Optional[Type[Any]] = None

    async def _arun(self, user_id: int, description: str, **kwargs) -> Any:
        async for session in get_session():
            repo = TaskRepository(session)
            task_in = TaskCreate(description=description)
            task = await repo.create_task(user_id=user_id, task_in=task_in)
            return {"id": task.id, "description": task.description}

    def _run(self, *args, **kwargs):
        raise NotImplementedError("Только async")

class DeleteTaskTool(BaseTool):
    name: str = "delete_task"
    description: str = "Удалить задачу по id. Обязательные параметры: user_id (int), task_id (int)."
    args_schema: Optional[Type[Any]] = None

    async def _arun(self, user_id: int, task_id: int, **kwargs) -> Any:
        async for session in get_session():
            repo = TaskRepository(session)
            task = await repo.get_task(task_id)
            if not task or task.user_id != user_id:
                return {"ok": False, "error": "Task not found or not owned by user"}
            await repo.delete_task(task_id)
            return {"ok": True}

    def _run(self, *args, **kwargs):
        raise NotImplementedError("Только async")

