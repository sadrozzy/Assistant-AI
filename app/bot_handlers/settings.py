from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.db.session import get_session

router = Router()

settings_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Google интеграция", callback_data="google_settings")],
        [InlineKeyboardButton(text="Часовой пояс", callback_data="change_timezone")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
    ]
)

class SettingsStates(StatesGroup):
    waiting_for_timezone = State()

@router.callback_query(lambda c: c.data == "settings_menu")
async def show_settings_menu(callback):
    await callback.message.edit_text(
        "⚙️ Настройки:\n\nВыберите опцию:",
        reply_markup=settings_menu
    )

@router.callback_query(lambda c: c.data == "change_timezone")
async def change_timezone_callback(callback, state: FSMContext):
    await callback.message.edit_text(
        "Введите ваш часовой пояс в формате +03:00, -05:00 и т.д.\nНапример, для Москвы — +03:00"
    )
    await state.set_state(SettingsStates.waiting_for_timezone)

@router.message(SettingsStates.waiting_for_timezone)
async def set_timezone_handler(message: Message, state: FSMContext):
    tz = message.text.strip()
    import re
    if not re.match(r"^[+-](0\d|1[0-4]):[0-5]\d$", tz):
        await message.answer("Некорректный формат. Введите, например, +03:00 или -05:00")
        return
    async for session in get_session():
        from app.db.repositories.user_repo import UserRepository
        user_repo = UserRepository(session)
        user = await user_repo.get_or_create_user(
            telegram_id=message.from_user.id,
            name=message.from_user.full_name or None,
        )
        user.timezone = tz
        await session.commit()
        await message.answer(f"Часовой пояс обновлён: {tz}")
        await state.clear()
        # Возврат в меню настроек
        await message.answer(
            "⚙️ Настройки:\n\nВыберите опцию:",
            reply_markup=settings_menu
        ) 