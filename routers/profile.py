from aiogram import Router, F
from aiogram.types import Message

from db.database import AsyncSessionLocal
from db.models import Booking, Subscription
from sqlalchemy import select

router = Router(name="profile_router")


@router.message(F.text == "Мои занятия 📅")
async def my_bookings(message: Message):
    async with AsyncSessionLocal() as session:
        bookings = await session.execute(
            select(Booking).where(Booking.user_id == message.from_user.id).order_by(Booking.date.desc())
        )
        bookings = bookings.scalars().all()

        if not bookings:
            await message.answer("У тебя пока нет записей")
            return

        text = "Твои занятия:\n\n"
        for b in bookings[:10]:
            status_emoji = {"paid": "✅", "pending": "⏳", "done": "✅", "cancelled": "❌"}.get(b.status, "❓")
            text += f"{status_emoji} {b.date} {b.time} • {b.trainer}\n"

        await message.answer(text)


@router.message(F.text == "Мои абонементы 🎟")
async def my_subscriptions(message: Message):
    async with AsyncSessionLocal() as session:
        subs = await session.execute(
            select(Subscription).where(Subscription.user_id == message.from_user.id)
        )
        subs = subs.scalars().all()

        if not subs:
            await message.answer("У тебя нет активных абонементов")
        else:
            text = "Твои абонементы:\n\n"
            for s in subs:
                text += f"• Осталось {s.classes_left} из {s.classes_total}\n"
            await message.answer(text)
