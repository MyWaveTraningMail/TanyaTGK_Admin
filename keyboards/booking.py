from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def trainers_keyboard(trainers: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for trainer in sorted(trainers):
        builder.row(
            InlineKeyboardButton(
                text=f"👩‍🦱 {trainer}",
                callback_data=f"trainer_{trainer}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад в меню", callback_data="cancel_booking")
    )
    return builder.as_markup()


def dates_keyboard(dates: list[str], trainer: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for date in dates:
        # Красивый формат: 15 марта, пт
        day, month_name, weekday_short = date.split("|")
        text = f"{day} {month_name} • {weekday_short}"
        builder.row(
            InlineKeyboardButton(
                text=text,
                callback_data=f"date_{trainer}_{date.split('|')[0].strip()}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад к тренерам", callback_data="back_to_trainers")
    )
    return builder.as_markup()


def times_keyboard(times: list[dict], trainer: str, date_str: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for slot in times:
        time = slot["time"]
        free = slot["free"]
        price = slot["price"]
        text = f"{time} • {free} мест(а) • {price} ₽"
        builder.row(
            InlineKeyboardButton(
                text=text,
                callback_data=f"time_{trainer}_{date_str}_{time}_{price}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="◀️ Назад к датам", callback_data=f"back_to_dates_{trainer}")
    )
    return builder.as_markup()


def payment_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Разовое занятие", callback_data="pay_single"),
        InlineKeyboardButton(text="Оплатить абонементом", callback_data="pay_subscription")
    )
    return builder.as_markup()


def confirm_booking_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить запись", callback_data="confirm_booking"),
        InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_booking")
    )
    return builder.as_markup()
