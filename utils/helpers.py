from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from db.models import Booking


def format_price(amount: int) -> str:
    """Форматирует сумму в рубли."""
    return f"{amount} ₽"


async def update_user_activity(user_id: int) -> None:
    """
    Обновляет время последней активности пользователя.
    Используется для отслеживания неактивных пользователей (шаг 11).
    
    Args:
        user_id: Telegram ID пользователя
    """
    from db.models import User
    from db.database import AsyncSessionLocal
    from sqlalchemy import select
    
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                user.last_activity = datetime.utcnow()
                await session.commit()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка при обновлении last_activity для {user_id}: {e}")


def hours_to_lesson(booking: "Booking") -> float:
    """
    Вычисляет количество часов до начала занятия.
    
    Args:
        booking: Объект бронирования с полями date ("15 марта 2025") и time ("HH:MM")
    
    Returns:
        Количество часов до начала занятия (может быть отрицательным, если занятие в прошлом)
    
    Example:
        >>> booking.date = "27 ноября 2025"
        >>> booking.time = "10:00"
        >>> hours = hours_to_lesson(booking)  # Примерно 10.5 часов
    """
    try:
        # Парсим дату в формате "27 ноября 2025" и время "10:00"
        lesson_datetime = datetime.strptime(f"{booking.date} {booking.time}", "%d %B %Y %H:%M")
        now = datetime.now()
        delta = lesson_datetime - now
        return delta.total_seconds() / 3600
    except ValueError as e:
        # Если формат некорректный, логируем и возвращаем 0
        print(f"Ошибка парсинга даты/времени: {booking.date} {booking.time} — {e}")
        return 0

