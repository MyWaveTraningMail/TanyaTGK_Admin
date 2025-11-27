from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def feedback_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Отменить", callback_data="cancel_feedback")]])
