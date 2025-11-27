# keyboards/lesson_type.py
"""Клавиатуры для выбора типа занятия."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def lesson_type_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора типа занятия."""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🆓 Пробное — 900 ₽", callback_data="lesson_trial")
    )
    builder.row(
        InlineKeyboardButton(text="👥 Групповое разовое — 1000 ₽", callback_data="lesson_group_single")
    )
    builder.row(
        InlineKeyboardButton(text="🎟 Групповое по абонементу", callback_data="lesson_group_subscription")
    )
    builder.row(
        InlineKeyboardButton(text="👤 Индивидуальное — 1800 ₽", callback_data="lesson_individual")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Отменить", callback_data="cancel_booking")
    )
    
    return builder.as_markup()
