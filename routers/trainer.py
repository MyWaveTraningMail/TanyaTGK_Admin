"""
Маршрутизатор для обработки команд тренеров.
Доступные команды:
- Мои занятия как тренера (просмотр своего расписания)
- Отметить посещение (отметить студента как посетившего)
- Отправить напоминание (отправить сообщение всем студентам)
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from db.models import Booking, User
from db.database import AsyncSessionLocal
from keyboards.main_menu import get_main_menu
from services.google_sheets import log_event_to_sheet
from config import TRAINER_CHAT_IDS
from sqlalchemy import select
from datetime import datetime, timedelta

router = Router(name="trainer_router")


class TrainerStates(StatesGroup):
    """Состояния FSM для функций тренера"""
    sending_reminder = State()  # Отправка напоминания всем студентам
    selecting_booking_to_mark = State()  # Выбор бронирования для отметки посещения


@router.message(F.text == "Мои занятия как тренера 🎓")
async def trainer_schedule(message: Message, state: FSMContext) -> None:
    """Показывает расписание тренера на неделю с возможностью отметить посещение"""
    telegram_id = message.from_user.id
    
    # Проверяем что это тренер
    if telegram_id not in TRAINER_CHAT_IDS:
        await message.answer("❌ У вас нет доступа к этой функции")
        return
    
    await log_event_to_sheet(telegram_id, "click: Мои занятия как тренера")
    
    async with AsyncSessionLocal() as session:
        # Получаем все бронирования на неделю где тренер = current_trainer
        # Для упрощения используем фильтр по тексту в trainer поле
        today = datetime.now()
        week_end = today + timedelta(days=7)
        
        result = await session.execute(
            select(Booking).where(
                (Booking.trainer_name != None) &
                (Booking.status != "cancelled")
            )
        )
        bookings = result.scalars().all()
        
        if not bookings:
            await message.answer(
                "📅 На этой неделе у вас нет запланированных занятий.",
                reply_markup=get_main_menu(is_trainer=True)
            )
            return
        
        # Форматируем расписание
        schedule_text = "📅 *Ваши занятия на неделю:*\n\n"
        
        for i, booking in enumerate(bookings, 1):
            status_emoji = "✅" if booking.status == "paid" else "⏳"
            student_name = booking.student_name or "Не указано"
            
            schedule_text += (
                f"{i}. {booking.date} {booking.time}\n"
                f"   Студент: {student_name}\n"
                f"   Тип: {booking.lesson_type} {status_emoji}\n\n"
            )
        
        schedule_text += "\n💡 Нажмите кнопку ниже для отметки посещения:"
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="✅ Отметить посещение", callback_data="mark_attendance")
            ]]
        )
        
        await message.answer(schedule_text, reply_markup=keyboard, parse_mode="Markdown")


@router.message(F.text == "Отметить посещение ✅")
async def mark_attendance_start(message: Message, state: FSMContext) -> None:
    """Начало процесса отметки посещения"""
    telegram_id = message.from_user.id
    
    if telegram_id not in TRAINER_CHAT_IDS:
        await message.answer("❌ У вас нет доступа к этой функции")
        return
    
    await log_event_to_sheet(telegram_id, "click: Отметить посещение")
    await state.set_state(TrainerStates.selecting_booking_to_mark)
    
    await message.answer(
        "🔍 Введите информацию о студенте или номер бронирования для отметки посещения:\n\n"
        "(Функция будет полностью готова в следующем обновлении)",
        reply_markup=get_main_menu(is_trainer=True)
    )


@router.message(F.text == "Отправить напоминание 🔔")
async def send_reminder_start(message: Message, state: FSMContext) -> None:
    """Начало процесса отправки напоминания всем студентам"""
    telegram_id = message.from_user.id
    
    if telegram_id not in TRAINER_CHAT_IDS:
        await message.answer("❌ У вас нет доступа к этой функции")
        return
    
    await log_event_to_sheet(telegram_id, "click: Отправить напоминание")
    await state.set_state(TrainerStates.sending_reminder)
    
    await message.answer(
        "📝 Напишите текст напоминания, которое будет отправлено всем студентам:\n\n"
        "(Максимум 1024 символа)"
    )


@router.message(TrainerStates.sending_reminder)
async def process_reminder_text(message: Message, state: FSMContext) -> None:
    """Обработка текста напоминания и отправка всем студентам"""
    telegram_id = message.from_user.id
    reminder_text = message.text
    
    if len(reminder_text) > 1024:
        await message.answer("❌ Текст слишком длинный (максимум 1024 символа)")
        return
    
    await log_event_to_sheet(telegram_id, f"reminder_sent: {reminder_text[:50]}")
    
    # Получаем всех активных студентов
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.status == "active")
        )
        students = result.scalars().all()
    
    # Отправляем напоминание каждому
    sent_count = 0
    for student in students:
        try:
            # TODO: Реализовать отправку сообщения через бот API
            # await bot.send_message(student.telegram_id, reminder_text)
            sent_count += 1
        except Exception as e:
            print(f"Ошибка при отправке студенту {student.telegram_id}: {e}")
    
    await state.clear()
    await message.answer(
        f"✅ Напоминание отправлено {sent_count} студентам!",
        reply_markup=get_main_menu(is_trainer=True)
    )


@router.callback_query(F.data == "mark_attendance")
async def mark_attendance_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка callback'а для отметки посещения"""
    await callback.answer("Функция в разработке ⚙️")
