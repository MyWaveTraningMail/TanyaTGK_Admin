from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def simple_payment_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Оплатить", callback_data="pay")]])
    return kb
