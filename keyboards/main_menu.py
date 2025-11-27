from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from utils.constants import MAIN_MENU_BUTTONS, TRAINER_MENU_BUTTONS


def get_main_menu(is_trainer: bool = False) -> ReplyKeyboardMarkup:
    """Возвращает главное меню в зависимости от роли пользователя"""
    if is_trainer:
        menu_items = TRAINER_MENU_BUTTONS
    else:
        menu_items = MAIN_MENU_BUTTONS
    
    buttons = [[KeyboardButton(text=text)] for text in menu_items.keys()]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=False)
