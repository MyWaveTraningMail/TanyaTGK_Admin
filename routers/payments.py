from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart

from db.models import Booking
from db.database import AsyncSessionLocal

router = Router(name="payments_router")


@router.message(CommandStart(deep_link=True))
async def handle_payment_return(message: Message):
    if not message.text.startswith("/start paid_"):
        return

    try:
        booking_id = int(message.text.split("paid_")[1])
    except:
        await message.answer("❌ Оплата не распознана")
        return

    async with AsyncSessionLocal() as session:
        booking = await session.get(Booking, booking_id)
        if not booking:
            await message.answer("❌ Запись не найдена")
            return

        if booking.status == "paid":
            await message.answer("✅ Ты уже оплатил(а) это занятие!\nСкоро начнём 💪")
            return

        booking.status = "paid"
        await session.commit()

        await message.answer(
            "🎉 Оплата прошла успешно!\n"
            f"Запись на {booking.trainer} — {booking.date} в {booking.time} подтверждена!\n\n"
            "Напомню за 24 и 2 часа до занятия ⏰"
        )
