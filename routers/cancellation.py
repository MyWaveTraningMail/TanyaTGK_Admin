"""
🚫 Маршрутизатор отмены и переноса бронирований (Шаг 5.3).

Реализует правило 10 часов:
- Если до занятия >= 10 часов: разрешить отмену/перенос без потерь
- Если до занятия < 10 часов: запретить без потерь
  * Для абонемента: считать занятие отгулянным (спишется)
  * Для разовой оплаты: деньги не вернутся
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from db.models import Booking, Subscription
from db.database import AsyncSessionLocal
from keyboards.booking import dates_keyboard
from services.google_sheets import (
    get_available_dates, log_event_to_sheet, update_free_slots
)
from utils.helpers import hours_to_lesson
from sqlalchemy import select

logger = logging.getLogger(__name__)
router = Router(name="cancellation_router")


class RescheduleStates(StatesGroup):
    """Состояния FSM для переноса бронирования"""
    choosing_new_date = State()
    choosing_new_time = State()


@router.callback_query(F.data.startswith("cancel_"))
async def cancel_booking(callback: CallbackQuery):
    """Обработка отмены бронирования с проверкой 10-часового правила"""
    try:
        booking_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка при обработке запроса", show_alert=True)
        return
    
    telegram_id = callback.from_user.id
    
    async with AsyncSessionLocal() as session:
        booking = await session.get(Booking, booking_id)
        
        if not booking or booking.user_id != telegram_id:
            await callback.answer("❌ Запись не найдена", show_alert=True)
            return
        
        if booking.status == "cancelled":
            await callback.answer("ℹ️ Эта запись уже отменена", show_alert=True)
            return
        
        # ⏰ ПРАВИЛО 10 ЧАСОВ (Шаг 5.3)
        hours_remaining = hours_to_lesson(booking)
        
        if hours_remaining < 10:
            # ❌ Менее 10 часов - отмена с потерями
            if booking.lesson_type == "group_subscription":
                # Абонемент: занятие считается отгулянным
                booking.status = "late_cancel"  # Поздняя отмена
                await session.commit()
                
                # Возвращаем место в Sheets если был row_index
                if hasattr(booking, 'row_index'):
                    await update_free_slots(booking.row_index, delta=+1)
                
                await log_event_to_sheet(
                    telegram_id, 
                    f"late_cancel_subscription: {booking.trainer} {booking.date} (занятие учтено)"
                )
                
                await callback.answer(
                    "⏰ Менее 10 часов до занятия!\n\n"
                    "❌ Отмену без потерь уже нельзя сделать.\n"
                    "✓ Занятие будет считаться пройденным и спишется с абонемента.\n\n"
                    "Если это необходимо обсудить, напиши администратору!",
                    show_alert=True
                )
            else:
                # Разовая оплата: деньги не вернутся
                booking.status = "late_cancel"
                await session.commit()
                
                await log_event_to_sheet(
                    telegram_id,
                    f"late_cancel_single: {booking.trainer} {booking.date} (платёж не возвращается)"
                )
                
                await callback.answer(
                    "⏰ Менее 10 часов до занятия!\n\n"
                    "❌ Отмену нельзя сделать.\n"
                    "💰 Оплата не будет возвращена.\n\n"
                    "Если это необходимо обсудить, напиши администратору!",
                    show_alert=True
                )
            
            await callback.message.edit_text(
                f"❌ Запись не может быть отменена\n\n"
                f"📅 {booking.date}\n"
                f"🕐 {booking.time}\n"
                f"👨‍🏫 {booking.trainer}\n\n"
                f"⏰ Менее 10 часов до начала занятия",
                parse_mode="HTML"
            )
            return
        
        # ✅ 10+ часов - разрешить отмену без потерь
        booking.status = "cancelled"
        
        # Если по абонементу, вернуть класс в пул
        if booking.lesson_type == "group_subscription":
            result = await session.execute(
                select(Subscription).where(Subscription.user_id == telegram_id)
            )
            active_sub = result.scalar_one_or_none()
            if active_sub:
                active_sub.classes_left += 1
        
        await session.commit()
        
        # Возвращаем место в Sheets
        if hasattr(booking, 'row_index'):
            await update_free_slots(booking.row_index, delta=+1)
        
        await log_event_to_sheet(
            telegram_id, 
            f"cancel_early: {booking.trainer} {booking.date} {booking.time} ({hours_remaining:.1f} часов)"
        )
        
        await callback.answer("✅ Запись отменена успешно!", show_alert=True)
        await callback.message.edit_text(
            f"✅ Запись отменена\n\n"
            f"📅 {booking.date}\n"
            f"🕐 {booking.time}\n"
            f"👨‍🏫 {booking.trainer}\n\n"
            f"⏰ За {hours_remaining:.1f} часов до начала (без потерь)",
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("reschedule_"))
async def reschedule_booking(callback: CallbackQuery, state: FSMContext):
    """Обработка переноса бронирования с проверкой 10-часового правила"""
    try:
        booking_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка при обработке запроса", show_alert=True)
        return
    
    telegram_id = callback.from_user.id
    
    async with AsyncSessionLocal() as session:
        booking = await session.get(Booking, booking_id)
        
        if not booking or booking.user_id != telegram_id:
            await callback.answer("❌ Запись не найдена", show_alert=True)
            return
        
        if booking.status == "cancelled":
            await callback.answer("ℹ️ Эта запись уже отменена", show_alert=True)
            return
        
        # ⏰ ПРАВИЛО 10 ЧАСОВ для переноса
        hours_remaining = hours_to_lesson(booking)
        
        if hours_remaining < 10:
            await callback.answer(
                "⏰ Менее 10 часов до занятия!\n\n"
                "❌ Перенос уже не возможен.\n"
                "💡 Пожалуйста, отмени эту запись и забронируй новое время,\n"
                "   или напиши администратору для помощи.",
                show_alert=True
            )
            return
        
        # ✅ 10+ часов - разрешить перенос
        await state.set_state(RescheduleStates.choosing_new_date)
        await state.update_data(
            old_booking_id=booking_id,
            lesson_type=booking.lesson_type,
            payment_type=booking.payment_type,
            trainer=booking.trainer,
            hours_remaining=hours_remaining
        )
        
        await log_event_to_sheet(
            telegram_id,
            f"reschedule_start: {booking.trainer} {booking.date} {booking.time} ({hours_remaining:.1f} часов)"
        )
        
        dates = await get_available_dates(booking.trainer)
        if not dates:
            await callback.answer("😔 Нет свободных дат у этого тренера", show_alert=True)
            return
        
        await callback.message.edit_text(
            f"📅 Перенос занятия\n\n"
            f"Текущее: {booking.date} {booking.time}\n"
            f"Тренер: {booking.trainer}\n\n"
            f"⏰ Осталось {hours_remaining:.1f} часов до занятия\n\n"
            f"Выбери новую дату:",
            reply_markup=dates_keyboard(dates, booking.trainer),
            parse_mode="HTML"
        )
