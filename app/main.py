from fastapi import FastAPI
from app.api import tasks, calendar
from app.utils.logger import logger

logger = logger("fastapi")

app = FastAPI()
logger.info("FastAPI app created")

app.include_router(tasks.router)
app.include_router(calendar.router)
logger.info("Routers included: tasks, calendar")
