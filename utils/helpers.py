from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from db.models import Booking


def format_price(amount: int) -> str:
    """Форматирует сумму в рубли."""
    return f"{amount} ₽"


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

