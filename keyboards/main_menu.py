from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from utils.constants import MAIN_MENU_BUTTONS

def get_main_menu() -> ReplyKeyboardMarkup:
    buttons = [[KeyboardButton(text=text)] for text in MAIN_MENU_BUTTONS.keys()]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=False)
