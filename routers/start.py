from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from db.models import User
from db.database import AsyncSessionLocal
from keyboards.main_menu import get_main_menu
from utils.constants import WELCOME_TEXT

router = Router(name="start_router")


from sqlalchemy import select
async def register_user_if_not_exists(telegram_id: int, full_name: str, username: str | None):
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
    await state.clear()
    await register_user_if_not_exists(
        telegram_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username,
    )
    await message.answer(
        WELCOME_TEXT,
        reply_markup=get_main_menu(),
        disable_web_page_preview=True,
    )


@router.message(F.text == "Начать 🚀")
async def start_button(message: Message, state: FSMContext):
    await state.clear()
    await register_user_if_not_exists(
        telegram_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username,
    )
    await message.answer(
        WELCOME_TEXT,
        reply_markup=get_main_menu(),
        disable_web_page_preview=True,
    )


@router.message(F.text == "◀️ В главное меню")
async def back_to_main_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=get_main_menu())
