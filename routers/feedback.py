from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from config import ADMIN_CHAT_ID

router = Router(name="feedback_router")


class FeedbackStates(StatesGroup):
    waiting_rating = State()
    waiting_text = State()


@router.message(F.text == "Оставить отзыв ⭐")
async def start_feedback(message: Message, state: FSMContext):
    builder = InlineKeyboardBuilder()
    for i in range(1, 6):
        builder.add(InlineKeyboardButton(text=f"{i} ⭐", callback_data=f"rate_{i}"))
    builder.adjust(5)

    await state.set_state(FeedbackStates.waiting_rating)
    await message.answer("Оцени занятие от 1 до 5 ⭐", reply_markup=builder.as_markup())


@router.callback_query(FeedbackStates.waiting_rating, F.data.startswith("rate_"))
async def get_rating(callback: CallbackQuery, state: FSMContext):
    rating = callback.data.split("_")[1]
    await state.update_data(rating=rating)
    await state.set_state(FeedbackStates.waiting_text)

    await callback.message.edit_text(f"Спасибо за {rating} ⭐!\n\nНапиши свой отзыв (можно с фото/видео):")


@router.message(FeedbackStates.waiting_text)
async def get_feedback_text(message: Message, state: FSMContext):
    data = await state.get_data()
    text = f"Новый отзыв ⭐ {data['rating']}\nОт: @{message.from_user.username or 'без имени'}\n\n{message.text or 'Без текста'}"

    await message.bot.send_message(ADMIN_CHAT_ID, text)
    if message.photo:
        await message.bot.send_photo(ADMIN_CHAT_ID, message.photo[-1].file_id, caption=text)
    if message.video:
        await message.bot.send_video(ADMIN_CHAT_ID, message.video.file_id, caption=text)

    await message.answer("Спасибо за отзыв! 💜 Это очень важно для нас")
    await state.clear()
