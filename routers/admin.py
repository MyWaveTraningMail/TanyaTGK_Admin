from aiogram import Router, F
from aiogram.types import Message

from config import ADMIN_CHAT_ID

router = Router(name="admin_router")


@router.message(F.text == "Связаться с администратором ✉️")
async def contact_admin(message: Message):
    await message.answer("Напиши своё сообщение — я передам администратору")
    # Дальше можно добавить FSM для пересылки
