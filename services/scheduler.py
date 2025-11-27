import logging
from datetime import datetime, timedelta

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

from db.models import Booking
from db.database import AsyncSessionLocal
from utils.constants import REMINDER_24H, REMINDER_2H

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="Europe/Moscow")


async def send_reminder(bot: Bot, booking: Booking, text: str, buttons: list):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    try:
        await bot.send_message(
            chat_id=booking.user_id,
            text=text,
            reply_markup=keyboard
        )
        logger.info(f"Напоминание отправлено: user {booking.user_id}, booking {booking.id}")
    except Exception as e:
        logger.error(f"Не удалось отправить напоминание пользователю {booking.user_id}: {e}")


async def schedule_reminders(bot: Bot, booking: Booking):
    lesson_dt = datetime.strptime(f"{booking.date} {booking.time}", "%d %B %Y %H:%M")
    
    reminder_24 = lesson_dt - timedelta(hours=24)
    reminder_2 = lesson_dt - timedelta(hours=2)

    if reminder_24 > datetime.now():
        scheduler.add_job(
            send_24h_reminder,
            DateTrigger(run_date=reminder_24),
            args=[bot, booking.id],
            id=f"reminder_24h_{booking.id}",
            replace_existing=True
        )

    if reminder_2 > datetime.now():
        scheduler.add_job(
            send_2h_reminder,
            DateTrigger(run_date=reminder_2),
            args=[bot, booking.id],
            id=f"reminder_2h_{booking.id}",
            replace_existing=True
        )


async def send_24h_reminder(bot: Bot, booking_id: int):
    async with AsyncSessionLocal() as session:
        booking = await session.get(Booking, booking_id)
        if not booking or booking.status in ["cancelled", "done"]:
            return
        booking.reminder_24_sent = True
        await session.commit()

        buttons = [
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{booking.id}")],
            [InlineKeyboardButton(text="🔄 Перенести", callback_data=f"reschedule_{booking.id}")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_{booking.id}")]
        ]
        await send_reminder(bot, booking, REMINDER_24H, buttons)


async def send_2h_reminder(bot: Bot, booking_id: int):
    async with AsyncSessionLocal() as session:
        booking = await session.get(Booking, booking_id)
        if not booking or booking.status in ["cancelled", "done"]:
            return
        booking.reminder_2_sent = True
        await session.commit()

        buttons = [[InlineKeyboardButton(text="Я здесь! 💪", callback_data=f"im_here_{booking.id}")]]
        await send_reminder(bot, booking, REMINDER_2H, buttons)


async def setup_scheduler(bot: Bot):
    scheduler.start()
    logger.info("APScheduler запущен: напоминания активны")
