import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import TELEGRAM_BOT_TOKEN, ADMIN_CHAT_ID
from db.database import init_db
from routers import (
    start,
    booking,
    payments,
    profile,
    feedback,
    faq,
    admin,
    trainer,
)
from services.scheduler import setup_scheduler
from utils.logging_config import setup_logging

# Настраиваем логирование
setup_logging()

logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    """Действия при старте бота"""
    await init_db()
    await setup_scheduler(bot)

    welcome_msg = "🤖 <b>Бот Pilates Reformer успешно запущен!</b>"
    await bot.send_message(ADMIN_CHAT_ID, welcome_msg, parse_mode=ParseMode.HTML)
    logger.info("Бот запущен и готов к работе")


async def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не указан в .env!")
        return

    bot = Bot(
        token=TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Подключаем роутеры
    dp.include_router(start.router)
    dp.include_router(booking.router)
    dp.include_router(trainer.router)  # Маршруты тренеров
    dp.include_router(payments.router)
    dp.include_router(profile.router)
    dp.include_router(feedback.router)
    dp.include_router(faq.router)
    dp.include_router(admin.router)

    # Запуск планировщика и уведомление админа
    dp.startup.register(on_startup)

    logger.info("Запуск бота в режиме polling...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен вручную")
