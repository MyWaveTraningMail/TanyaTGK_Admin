from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from db.models import User
from db.database import AsyncSessionLocal
from keyboards.main_menu import get_main_menu
from utils.constants import WELCOME_TEXT
from config import TRAINER_CHAT_IDS
from services.google_sheets import log_event_to_sheet

router = Router(name="start_router")

from sqlalchemy import select


async def register_user_if_not_exists(telegram_id: int, full_name: str, username: str | None):
    """Регистрация пользователя если его нет в БД"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            new_user = User(
                telegram_id=telegram_id,
                full_name=full_name or username or "Не указано",
            )
            session.add(new_user)
            await session.commit()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Команда /start: регистрация и показ меню по ролям"""
    telegram_id = message.from_user.id
    
    await state.clear()
    await register_user_if_not_exists(
        telegram_id=telegram_id,
        full_name=message.from_user.full_name,
        username=message.from_user.username,
    )
    
    # Логируем событие
    await log_event_to_sheet(telegram_id, "message: /start")
    
    # Определяем роль пользователя
    is_trainer = telegram_id in TRAINER_CHAT_IDS
    
    # Показываем приветствие с информацией о роли
    role_info = ""
    if is_trainer:
        role_info = "\n\n🎓 *Вы вошли как тренер*"
    
    await message.answer(
        f"{WELCOME_TEXT}{role_info}",
        reply_markup=get_main_menu(is_trainer=is_trainer),
        disable_web_page_preview=True,
        parse_mode="Markdown"
    )


@router.message(F.text == "Начать 🚀")
async def start_button(message: Message, state: FSMContext):
    """Кнопка 'Начать' - запускает тот же процесс что и /start"""
    telegram_id = message.from_user.id
    
    await state.clear()
    await register_user_if_not_exists(
        telegram_id=telegram_id,
        full_name=message.from_user.full_name,
        username=message.from_user.username,
    )
    
    # Логируем событие
    await log_event_to_sheet(telegram_id, "click: Начать")
    
    # Определяем роль пользователя
    is_trainer = telegram_id in TRAINER_CHAT_IDS
    
    # Показываем приветствие с информацией о роли
    role_info = ""
    if is_trainer:
        role_info = "\n\n🎓 *Вы вошли как тренер*"
    
    await message.answer(
        f"{WELCOME_TEXT}{role_info}",
        reply_markup=get_main_menu(is_trainer=is_trainer),
        disable_web_page_preview=True,
        parse_mode="Markdown"
    )


@router.message(F.text == "◀️ В главное меню")
async def back_to_main_menu(message: Message, state: FSMContext):
    """Кнопка возврата в главное меню"""
    telegram_id = message.from_user.id
    
    await state.clear()
    
    # Логируем событие
    await log_event_to_sheet(telegram_id, "click: В главное меню")
    
    # Определяем роль пользователя
    is_trainer = telegram_id in TRAINER_CHAT_IDS
    
    await message.answer("Главное меню:", reply_markup=get_main_menu(is_trainer=is_trainer))
