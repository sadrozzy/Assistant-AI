from aiogram import Router
from aiogram.types import Message, InputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from app.services.langchain_tools import AddTaskTool
from app.db.session import get_session
from app.db.repositories.user_repo import UserRepository
import aiohttp
import os
import uuid
from app.config import settings
from app.services.sync_google_calendar import sync_task_with_google_calendar
from app.utils import parse_task_text
import assemblyai as aai
import asyncio

router = Router()

aai.settings.api_key = settings.ai.ASSEMBLYAI_API_KEY

processing_tasks = {}

@router.message(lambda m: m.voice is not None)
async def voice_message_handler(message: Message):
    try:
        file_id = message.voice.file_id
        file = await message.bot.get_file(file_id)
        file_path = file.file_path
        file_url = f"https://api.telegram.org/file/bot{message.bot.token}/{file_path}"
        local_filename = f"/tmp/{uuid.uuid4()}.ogg"
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as resp:
                with open(local_filename, "wb") as f:
                    f.write(await resp.read())

        cancel_markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Отменить", callback_data="cancel_processing")]]
        )
        processing_msg = await message.reply(
            "Обработка...",
            reply_markup=cancel_markup
        )

        task = asyncio.create_task(
            process_voice_logic(message, processing_msg, local_filename)
        )
        processing_tasks[processing_msg.message_id] = task
    except Exception as e:
        await message.answer("Произошла ошибка при обработке голосового сообщения.")

async def process_voice_logic(message: Message, processing_msg: Message, local_filename: str):
    try:
        transcriber = aai.Transcriber()
        config = aai.TranscriptionConfig(language_code="ru", speech_model=aai.SpeechModel.best)
        transcript = await asyncio.get_event_loop().run_in_executor(
            None, lambda: transcriber.transcribe(local_filename, config=config)
        )
        text = transcript.text if transcript.text else ""
        os.remove(local_filename)
        async for db_session in get_session():
            user_repo = UserRepository(db_session)
            user = await user_repo.get_or_create_user(
                telegram_id=message.from_user.id,
                name=message.from_user.full_name or None,
            )
            add_task_tool = AddTaskTool()
            result = await add_task_tool._arun(user_id=user.id, description=text)
            parsed = parse_task_text(text)
            ok, sync_msg = await sync_task_with_google_calendar(
                user,
                type('Task', (), {'id': result['id'], 'description': result.get('description', text)}),
                parsed
            )
            await processing_msg.edit_text(
                f"Голосовое сообщение распознано и задача добавлена: {result.get('description', text)}\n{sync_msg}"
            )
            break
    except asyncio.CancelledError:
        await processing_msg.edit_text("Обработка отменена.")
        return
    except Exception as e:
        await processing_msg.edit_text("Произошла ошибка при обработке голосового сообщения.")
    finally:
        if os.path.exists(local_filename):
            try:
                os.remove(local_filename)
            except Exception:
                pass
        processing_tasks.pop(processing_msg.message_id, None)

@router.callback_query(lambda c: c.data == "cancel_processing")
async def cancel_processing_handler(callback: CallbackQuery):
    msg_id = callback.message.message_id
    task = processing_tasks.get(msg_id)
    if task and not task.done():
        task.cancel()
        await callback.answer("Обработка отменена")
    else:
        await callback.answer("Обработка уже завершена или отменена", show_alert=True)
