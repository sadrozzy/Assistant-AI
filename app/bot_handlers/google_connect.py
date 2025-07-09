from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from app.db.session import get_session
from app.db.repositories.user_repo import UserRepository
from app.services.google_auth import get_google_auth_flow, get_auth_url, fetch_tokens
from app.utils.logger import logger

router = Router()
logger = logger("google-connect-handler")

@router.message(Command("google"))
async def google_handler(message: Message, state: FSMContext):
    await show_google_menu(message, message.from_user.id, state)

async def show_google_menu(target, user_id, state):
    async for session in get_session():
        user_repo = UserRepository(session)
        user = await user_repo.get_or_create_user(
            telegram_id=user_id,
            name=None,
        )
        if user.google_access_token and user.google_refresh_token:
            text = "✅ Google Calendar подключён!"
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Отключить", callback_data="google_disconnect")],
                ]
            )
        else:
            text = "❌ Google Calendar не подключён."
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔗 Подключить Google Calendar", callback_data="google_connect")],
                ]
            )
        await target.answer(text, reply_markup=keyboard)

@router.callback_query(lambda c: c.data == "google_connect")
async def google_connect_callback(callback: CallbackQuery, state: FSMContext):
    flow = get_google_auth_flow()
    auth_url = get_auth_url(flow)
    await state.update_data(google_flow=flow)
    await callback.message.answer(
        f"Перейдите по ссылке для авторизации Google и вставьте полученный код ниже:\n\n{auth_url}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Ввести код", callback_data="google_enter_code")],
            ]
        )
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "google_enter_code")
async def google_enter_code_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Пожалуйста, отправьте код авторизации одним сообщением.")
    await state.set_state("waiting_for_google_code")
    await callback.answer()

@router.message()
async def google_code_inline_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state != "waiting_for_google_code":
        return
    code = message.text.strip()
    data = await state.get_data()
    flow = data.get("google_flow")
    if not flow:
        await message.answer("Сначала выберите 'Подключить Google Calendar' в меню.")
        return
    try:
        credentials = fetch_tokens(flow, code)
        async for session in get_session():
            user_repo = UserRepository(session)
            user = await user_repo.get_or_create_user(
                telegram_id=message.from_user.id,
                name=message.from_user.full_name or None,
            )
            user.google_access_token = credentials.token
            user.google_refresh_token = credentials.refresh_token
            user.google_token_expiry = credentials.expiry.isoformat()
            await session.commit()
            await message.answer("Google аккаунт успешно привязан!")
            await show_google_menu(message, message.from_user.id, state)
        await state.clear()
    except Exception as e:
        logger.exception(f"Ошибка при получении токенов Google: {e}")
        await message.answer(
            "Ошибка авторизации Google. Код некорректен или устарел. "
            "Пожалуйста, попробуйте ещё раз: скопируйте новый код из браузера и отправьте его сюда."
        )

@router.callback_query(lambda c: c.data == "google_disconnect")
async def google_disconnect_callback(callback: CallbackQuery, state: FSMContext):
    async for session in get_session():
        user_id = callback.from_user.id
        user_repo = UserRepository(session)
        user = await user_repo.get_or_create_user(
            telegram_id=user_id,
            name=callback.from_user.full_name or None,
        )
        user.google_access_token = None
        user.google_refresh_token = None
        user.google_token_expiry = None
        await session.commit()
        await show_google_menu(callback.message, user_id, state)
    await callback.answer() 