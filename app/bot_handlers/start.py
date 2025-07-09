from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

router = Router()


main_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Мои задачи", callback_data="show_tasks")],
        [InlineKeyboardButton(text="Создать задачу", callback_data="create_task")],
        [InlineKeyboardButton(text="Голосовой ввод", callback_data="voice_input")],
        [InlineKeyboardButton(text="Google Connect", callback_data="google_connect")],
    ]
)

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я — твой личный ассистент.\n\nВыбери действие:",
        reply_markup=main_menu
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
        "/google — подключение и управление Google Calendar\n"
        "\nМожешь также отправлять голосовые сообщения для создания задач!"
    )
