import logging
from datetime import datetime, timedelta

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from db.models import Booking, User
from db.database import AsyncSessionLocal
from utils.constants import REMINDER_12H, REMINDER_2H
from sqlalchemy import select

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
    """
    Планирует напоминания за 12 и 2 часа до начала занятия.
    
    Args:
        bot: Экземпляр aiogram Bot
        booking: Объект бронирования
    """
    lesson_dt = datetime.strptime(f"{booking.date} {booking.time}", "%d %B %Y %H:%M")
    
    reminder_12 = lesson_dt - timedelta(hours=12)
    reminder_2 = lesson_dt - timedelta(hours=2)

    if reminder_12 > datetime.now():
        scheduler.add_job(
            send_12h_reminder,
            DateTrigger(run_date=reminder_12),
            args=[bot, booking.id],
            id=f"reminder_12h_{booking.id}",
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


async def send_12h_reminder(bot: Bot, booking_id: int):
    """Отправляет напоминание за 12 часов до занятия."""
    async with AsyncSessionLocal() as session:
        booking = await session.get(Booking, booking_id)
        if not booking or booking.status in ["cancelled", "done"]:
            return
        booking.reminder_12_sent = True
        await session.commit()

        buttons = [
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{booking.id}")],
            [InlineKeyboardButton(text="🔄 Перенести", callback_data=f"reschedule_{booking.id}")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_{booking.id}")]
        ]
        await send_reminder(bot, booking, REMINDER_12H, buttons)


async def send_24h_reminder(bot: Bot, booking_id: int):
    """Отправляет напоминание за 12 часов до занятия (старое имя, для совместимости)."""
    await send_12h_reminder(bot, booking_id)


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
    """Инициализирует планировщик задач"""
    scheduler.start()
    
    # Добавляем ежедневную задачу для проверки неактивных пользователей (каждый день в 9:00)
    scheduler.add_job(
        check_inactive_users,
        IntervalTrigger(hours=24, start_date=datetime.now().replace(hour=9, minute=0, second=0)),
        args=[bot],
        id="check_inactive_users",
        replace_existing=True
    )
    
    logger.info("APScheduler запущен: напоминания и проверка неактивности активны")


async def check_inactive_users(bot: Bot):
    """
    Проверяет неактивных пользователей (не заходили 14+ дней).
    Отправляет им одно напоминание о повторном обращении.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=14)
    
    async with AsyncSessionLocal() as session:
        # Получаем пользователей, которые не активны 14+ дней
        # И которым еще не отправляли напоминание о неактивности
        result = await session.execute(
            select(User).where(
                (User.last_activity < cutoff_date) &
                ((User.last_inactivity_message_sent == None) |
                 (User.last_inactivity_message_sent < cutoff_date))
            )
        )
        inactive_users = result.scalars().all()
        
        sent_count = 0
        for user in inactive_users:
            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=(
                        "👋 Давно тебя не видели!\n\n"
                        "Приходи на пилатес — новых ощущений ждём! 🧘‍♀️\n\n"
                        "Нажми /start чтобы записаться на занятие."
                    )
                )
                user.last_inactivity_message_sent = datetime.utcnow()
                await session.commit()
                sent_count += 1
                logger.info(f"Напоминание о неактивности отправлено пользователю {user.telegram_id}")
            except Exception as e:
                logger.error(f"Ошибка при отправке напоминания пользователю {user.telegram_id}: {e}")
        
        logger.info(f"Проверка неактивности завершена: напоминания отправлены {sent_count} пользователям")
