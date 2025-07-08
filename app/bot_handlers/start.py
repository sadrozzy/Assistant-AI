from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я — твой личный ассистент.\n\n"
        "Я помогу управлять задачами, напоминаниями и календарём.\n"
        "Можешь отправлять мне текстовые или голосовые команды!\n"
        "\n/help — список команд."
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ Доступные команды:\n"
        "/start — приветствие и регистрация\n"
        "/help — помощь по командам\n"
        "/newtask — создать новую задачу\n"
        "/tasks — список задач\n"
        "/remind — настроить напоминание\n"
        "/calendar — события Google Calendar\n"
        "\nМожешь также отправлять голосовые сообщения для создания задач!"
    )
