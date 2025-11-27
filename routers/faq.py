import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.google_sheets import get_faq_answers

logger = logging.getLogger(__name__)
router = Router(name="faq_router")


@router.message(F.text == "FAQ ❓")
async def show_faq(message: Message):
    answers = await get_faq_answers()
    if not answers:
        await message.answer("❌ FAQ временно недоступен")
        return

    builder = InlineKeyboardBuilder()
    for q, a in answers:
        builder.row(
            InlineKeyboardBuilder().button(text=q, callback_data=f"faq_{q[:50]}").as_markup().inline_keyboard[0][0]
        )
    builder.row(
        InlineKeyboardBuilder().button(text="◀️ В меню", callback_data="back_to_menu").as_markup().inline_keyboard[0][0]
    )

    await message.answer("Часто задаваемые вопросы:", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("faq_"))
async def show_faq_answer(callback: CallbackQuery):
    question = callback.data[4:]
    answers = await get_faq_answers()
    answer = next((a for q, a in answers if q == question), "Ответ не найден")

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardBuilder().button(text="◀️ Назад к FAQ", callback_data="back_to_faq").as_markup().inline_keyboard[0][0]
    )

    await callback.message.edit_text(f"<b>{question}</b>\n\n{answer}", reply_markup=builder.as_markup(), parse_mode="HTML")
