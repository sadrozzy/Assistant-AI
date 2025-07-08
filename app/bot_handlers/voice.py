from aiogram import Router
from aiogram.types import Message
from app.services.transcription import TranscriptionService
from app.db.repositories.task_repo import TaskRepository
from app.db.session import get_session
from app.schemas.task import TaskCreate
import aiohttp
import os
import uuid
from app.utils.logger import logger

router = Router()
logger = logger("voice-handler")


@router.message(lambda m: m.voice is not None)
async def voice_message_handler(message: Message):
    try:
        file_id = message.voice.file_id
        logger.info(
            f"Received voice message from user {message.from_user.id}, file_id={file_id}"
        )
        file = await message.bot.get_file(file_id)
        file_path = file.file_path

        file_url = f"https://api.telegram.org/file/bot{message.bot.token}/{file_path}"
        local_filename = f"/tmp/{uuid.uuid4()}.ogg"
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                with open(local_filename, "wb") as f:
                    f.write(await resp.read())
        logger.info(f"Voice file downloaded to {local_filename}")
        # TODO: Конвертация ogg в wav при необходимости (например, через ffmpeg)
        transcription_service = TranscriptionService()
        text = await transcription_service.transcribe_audio(local_filename)
        logger.info(f"Transcription result: {text}")
        os.remove(local_filename)
        logger.info(f"Temp file {local_filename} removed")
        # TODO: Парсинг текста на наличие задачи и даты/времени
        task_in = TaskCreate(description=text)
        async for db_session in get_session():
            repo = TaskRepository(db_session)
            task = await repo.create_task(user_id=message.from_user.id, task_in=task_in)
            logger.info(
                f"Task created for user {message.from_user.id}: {task.description}"
            )
            # TODO: Создать событие в Google Calendar
            await message.answer(
                f"Голосовое сообщение распознано и задача добавлена: {task.description}"
            )
    except Exception as e:
        logger.exception(f"Error handling voice message: {e}")
