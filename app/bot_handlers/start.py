from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.bot_handlers.google_connect import show_google_menu
from app.db.session import get_session
from app.bot_handlers.settings import router as settings_router

router = Router()
router.include_router(settings_router)


main_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Мои задачи", callback_data="show_tasks")],
        [InlineKeyboardButton(text="Создать задачу", callback_data="create_task")],
        [InlineKeyboardButton(text="Голосовой ввод", callback_data="voice_input")],
        [InlineKeyboardButton(text="Настройки", callback_data="settings_menu")],
    ]
)

tasks_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
    ]
)

create_task_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
    ]
)

voice_input_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
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

@router.callback_query(lambda c: c.data == "main_menu")
async def show_main_menu(callback):
    await callback.message.edit_text(
        "👋 Привет! Я — твой личный ассистент.\n\nВыбери действие:",
        reply_markup=main_menu
    )

@router.callback_query(lambda c: c.data == "google_settings")
async def show_google_menu_callback(callback, state: FSMContext):
    await show_google_menu(callback.message, callback.from_user.id, state)

@router.callback_query(lambda c: c.data == "show_tasks")
async def show_tasks_menu(callback):
    await callback.message.edit_text(
        "Ваши задачи:",
        reply_markup=tasks_menu
    )

@router.callback_query(lambda c: c.data == "create_task")
async def show_create_task_menu(callback):
    guide = (
        "📋 <b>Как создать задачу:</b>\n"
        "\n"
        "1. <b>Быстрое добавление</b> — просто напишите текст, задача попадёт в Инбокс.\n"
        "   <i>Пример:</i> Купить молоко\n"
        "\n"
        "2. <b>Планирование</b> — добавьте дату/время, задача будет запланирована.\n"
        "   <i>Примеры:</i> Позвонить врачу завтра 10:00\n"
        "   Сдать отчёт 21.04 18:00\n"
        "\n"
        "3. <b>Напоминание</b> — добавьте !15м, !1ч, !1д в конце.\n"
        "   <i>Пример:</i> Встреча 21.04 15:00 !30м\n"
        "\n"
        "4. <b>Длительность</b> — укажите 1ч, 30м и т.д.\n"
        "   <i>Пример:</i> Тренировка 19:00 1ч\n"
        "\n"
        "5. <b>Поддерживаются сокращения дней недели и даты:</b> пн, вт, ср, чт, пт, сб, вс, сегодня, завтра, послезавтра, mon, tue и т.д.\n"
        "\n"
        "6. <b>Google Calendar</b> — если подключён, задачи автоматически попадают в календарь.\n"
        "\n"
        "<b>Примеры:</b>\n"
        "- Купить хлеб\n"
        "- Встреча с Петей завтра 14:00 !1ч\n"
        "- Позвонить маме 21.04 20:00\n"
        "- Сделать домашку 19:00 2ч !30м\n"
        "\n"
        "<b>Совет:</b> Для быстрой задачи — просто напишите текст. Для планирования — добавьте дату/время. Для напоминания — добавьте ! и интервал."
    )
    await callback.message.edit_text(
        guide,
        parse_mode="HTML",
        reply_markup=create_task_menu
    )

@router.callback_query(lambda c: c.data == "voice_input")
async def show_voice_input_menu(callback):
    await callback.message.edit_text(
        "Отправьте голосовое сообщение:",
        reply_markup=voice_input_menu
    )
