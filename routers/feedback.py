"""
⭐ Маршрутизатор отзывов с поддержкой медиа (Шаги 9.1-9.3).

Функции:
- Сбор рейтинга (1-5 звёзд)
- Сбор текста отзыва
- Опциональный приём фото/видео/документов (до 10 файлов)
- Логирование отзывов в Google Sheets Events
- Отправка админу со ссылками на медиа
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from config import ADMIN_CHAT_ID
from services.google_sheets import log_event_to_sheet

logger = logging.getLogger(__name__)
router = Router(name="feedback_router")


class FeedbackStates(StatesGroup):
    """Состояния для сбора отзыва (Шаги 9.1-9.3)"""
    waiting_rating = State()  # Выбор рейтинга
    waiting_text = State()    # Текст отзыва
    waiting_media = State()   # Приём медиа (фото/видео) - ШАГ 9.2
    adding_more_media = State()  # Добавление ещё файлов


@router.message(F.text == "Оставить отзыв ⭐")
async def start_feedback(message: Message, state: FSMContext):
    """Начало сбора отзыва - выбор рейтинга"""
    telegram_id = message.from_user.id
    
    await log_event_to_sheet(telegram_id, "click: Оставить отзыв")
    
    builder = InlineKeyboardBuilder()
    for i in range(1, 6):
        builder.add(InlineKeyboardButton(text=f"{i} ⭐", callback_data=f"rate_{i}"))
    builder.adjust(5)

    await state.set_state(FeedbackStates.waiting_rating)
    await message.answer("🌟 Оцени занятие от 1 до 5 звёзд:", reply_markup=builder.as_markup())


@router.callback_query(FeedbackStates.waiting_rating, F.data.startswith("rate_"))
async def get_rating(callback: CallbackQuery, state: FSMContext):
    """Обработка выбранного рейтинга"""
    rating = callback.data.split("_")[1]
    await state.update_data(rating=rating, media_files=[])
    await state.set_state(FeedbackStates.waiting_text)

    await callback.message.edit_text(
        f"✅ Спасибо за {rating} ⭐!\n\n"
        f"📝 Теперь напиши свой отзыв:\n"
        f"(он может быть коротким или развёрнутым)"
    )


@router.message(FeedbackStates.waiting_text)
async def get_feedback_text(message: Message, state: FSMContext):
    """Сбор текста отзыва (Шаг 9.1)"""
    if not message.text:
        await message.answer("❌ Пожалуйста, напиши текст отзыва")
        return
    
    feedback_text = message.text
    await state.update_data(feedback_text=feedback_text)
    
    # ШАГ 9.1: Предложение добавить медиа
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, добавить фото/видео", callback_data="add_media_yes"),
        InlineKeyboardButton(text="❌ Нет, отправить", callback_data="add_media_no")
    )
    
    await state.set_state(FeedbackStates.waiting_media)
    await message.answer(
        "💬 Отзыв принят!\n\n"
        f"«{feedback_text[:100]}{'...' if len(feedback_text) > 100 else ''}\"\n\n"
        "📸 Хочешь прикрепить фото или видео?",
        reply_markup=builder.as_markup()
    )


@router.callback_query(FeedbackStates.waiting_media, F.data == "add_media_yes")
async def start_media_upload(callback: CallbackQuery, state: FSMContext):
    """Начало загрузки медиа (Шаг 9.2)"""
    await state.update_data(media_files=[])
    await state.set_state(FeedbackStates.adding_more_media)
    
    await callback.message.edit_text(
        "📸 Пришли фото или видео\n\n"
        "Можно прикрепить несколько файлов (максимум 10)\n"
        "После каждого файла нажми кнопку ниже ⬇️",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="✅ Готово, отправить", callback_data="media_done"),
            InlineKeyboardButton(text="🗑️ Отменить медиа", callback_data="media_cancel")
        ).as_markup()
    )


@router.message(FeedbackStates.adding_more_media)
async def collect_media(message: Message, state: FSMContext):
    """Сбор медиа-файлов (Шаг 9.2)"""
    data = await state.get_data()
    media_files = data.get("media_files", [])
    
    media_info = None
    
    # Поддерживаем фото
    if message.photo:
        media_info = {
            "type": "photo",
            "file_id": message.photo[-1].file_id,
            "description": f"Фото {len(media_files) + 1}"
        }
    
    # Поддерживаем видео
    elif message.video:
        media_info = {
            "type": "video",
            "file_id": message.video.file_id,
            "description": f"Видео {len(media_files) + 1}"
        }
    
    # Поддерживаем документы
    elif message.document:
        media_info = {
            "type": "document",
            "file_id": message.document.file_id,
            "description": f"Документ: {message.document.file_name or 'файл'}"
        }
    
    else:
        await message.answer("❌ Пожалуйста, пришли фото, видео или документ")
        return
    
    # Проверяем лимит файлов
    if len(media_files) >= 10:
        await message.answer("⚠️ Максимум 10 файлов достигнут. Отправляю отзыв...")
        await send_final_feedback(message, state)
        return
    
    # Добавляем файл
    media_files.append(media_info)
    await state.update_data(media_files=media_files)
    
    await message.answer(
        f"✅ Добавлен: {media_info['description']}\n\n"
        f"📊 Файлов загружено: {len(media_files)}/10\n\n"
        f"Пришли ещё файл или нажми 'Готово' ⬇️",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="✅ Готово, отправить", callback_data="media_done"),
            InlineKeyboardButton(text="🗑️ Отменить всё", callback_data="media_cancel")
        ).as_markup()
    )


@router.callback_query(FeedbackStates.adding_more_media, F.data == "media_done")
async def finish_media_upload(callback: CallbackQuery, state: FSMContext):
    """Завершение загрузки медиа и отправка отзыва"""
    await send_final_feedback(callback.message, state)
    await callback.answer("✅ Отзыв отправлен!", show_alert=False)


@router.callback_query(FeedbackStates.adding_more_media, F.data == "media_cancel")
async def cancel_media_upload(callback: CallbackQuery, state: FSMContext):
    """Отмена загрузки медиа"""
    await state.update_data(media_files=[])
    await state.set_state(FeedbackStates.waiting_media)
    
    await callback.message.edit_text(
        "Медиа отменено. Хочешь добавить фото/видео?",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="✅ Да", callback_data="add_media_yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data="add_media_no")
        ).as_markup()
    )


@router.callback_query(FeedbackStates.waiting_media, F.data == "add_media_no")
async def skip_media_upload(callback: CallbackQuery, state: FSMContext):
    """Пропуск загрузки медиа и отправка отзыва"""
    await state.update_data(media_files=[])
    await send_final_feedback(callback.message, state)


async def send_final_feedback(message: Message, state: FSMContext):
    """Отправка финального отзыва администратору (Шаг 9.3)"""
    telegram_id = message.from_user.id
    data = await state.get_data()
    
    rating = data.get("rating", "?")
    feedback_text = data.get("feedback_text", "Нет текста")
    media_files = data.get("media_files", [])
    
    # Формируем сообщение для админа
    admin_text = (
        f"⭐ <b>Новый отзыв</b>\n\n"
        f"⭐ Рейтинг: {rating}/5\n"
        f"👤 От: {message.from_user.full_name or 'Без имени'} (@{message.from_user.username or 'нет username'})\n"
        f"📱 ID: {telegram_id}\n\n"
        f"💬 <b>Текст отзыва:</b>\n{feedback_text}\n\n"
        f"📎 Файлов прикреплено: {len(media_files)}"
    )
    
    # Отправляем основное сообщение админу
    try:
        await message.bot.send_message(ADMIN_CHAT_ID, admin_text, parse_mode="HTML")
        
        # Отправляем медиа-файлы (Шаг 9.3)
        for media in media_files:
            try:
                if media["type"] == "photo":
                    await message.bot.send_photo(
                        ADMIN_CHAT_ID,
                        media["file_id"],
                        caption=f"📸 {media['description']}"
                    )
                elif media["type"] == "video":
                    await message.bot.send_video(
                        ADMIN_CHAT_ID,
                        media["file_id"],
                        caption=f"🎥 {media['description']}"
                    )
                elif media["type"] == "document":
                    await message.bot.send_document(
                        ADMIN_CHAT_ID,
                        media["file_id"],
                        caption=f"📄 {media['description']}"
                    )
            except Exception as e:
                logger.error(f"Ошибка при отправке медиа админу: {e}")
        
        # Логируем отзыв в Events (Шаг 9.3)
        media_desc = f"({len(media_files)} файлов)" if media_files else "(без медиа)"
        await log_event_to_sheet(
            telegram_id,
            f"feedback: {rating}⭐ {media_desc} - {feedback_text[:50]}"
        )
        
        # Отправляем ответ клиенту
        media_thanks = f"\n\n📸 И спасибо за {len(media_files)} прикреплённых файлов!" if media_files else ""
        await message.answer(
            f"✅ <b>Спасибо за отзыв!</b>\n\n"
            f"💜 Ваше мнение очень важно для нас и помогает нам улучшаться{media_thanks}"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при отправке отзыва: {e}")
        await message.answer("❌ Ошибка при отправке отзыва. Попробуй ещё раз позже")
    
    await state.clear()
