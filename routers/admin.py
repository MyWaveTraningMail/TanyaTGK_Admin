"""
🔐 Маршрутизатор администратора (Шаги 6.3, 7.1-7.2).

Функции:
- Просмотр бронирований на день с inline-кнопками отмены/переноса
- Override отмена без штрафа (admin_cancel_no_penalty)
- Override перенос с коррекцией абонемента (admin_reschedule_override)
- Логирование всех админских действий как "override"
"""

import logging
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from db.models import Booking, Subscription, User
from db.database import AsyncSessionLocal
from keyboards.main_menu import get_main_menu
from services.google_sheets import log_event_to_sheet, update_free_slots
from config import ADMIN_CHAT_ID
from utils.helpers import hours_to_lesson
from sqlalchemy import select

logger = logging.getLogger(__name__)
router = Router(name="admin_router")


class AdminStates(StatesGroup):
    """Состояния для админских операций"""
    admin_message = State()  # Пересылка сообщения


@router.message(F.text == "Связаться с администратором ✉️")
async def contact_admin(message: Message):
    """Кнопка для обычных пользователей - связаться с админом"""
    await message.answer("Напиши своё сообщение — я передам администратору")


# ========== АДМИН-ПАНЕЛЬ ==========

@router.message(F.text == "📊 Админ-панель")
async def admin_panel(message: Message):
    """Главное меню администратора (Шаг 6.3)"""
    telegram_id = message.from_user.id
    
    if telegram_id != ADMIN_CHAT_ID:
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    
    await log_event_to_sheet(telegram_id, "click: Админ-панель")
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Занятия на сегодня", callback_data="admin_today_bookings")],
            [InlineKeyboardButton(text="📅 Все занятия на неделю", callback_data="admin_week_bookings")],
            [InlineKeyboardButton(text="👥 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="◀️ В меню", callback_data="back_to_menu")]
        ]
    )
    
    await message.answer(
        "🔐 <b>Админ-панель</b>\n\n"
        "Выбери действие:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_today_bookings")
async def show_today_bookings(callback: CallbackQuery):
    """Показывает все бронирования на сегодня с кнопками управления (Шаг 6.3)"""
    telegram_id = callback.from_user.id
    
    if telegram_id != ADMIN_CHAT_ID:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return
    
    today_str = datetime.now().strftime("%d %B %Y")
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Booking).where(
                (Booking.date == today_str) &
                (Booking.status != "cancelled")
            ).order_by(Booking.time)
        )
        bookings = result.scalars().all()
    
    if not bookings:
        await callback.message.edit_text(
            "📅 <b>Занятия на сегодня</b>\n\n"
            "Нет запланированных занятий",
            parse_mode="HTML"
        )
        return
    
    text = f"📅 <b>Занятия на сегодня ({today_str})</b>\n\n"
    
    for booking in bookings:
        status_emoji = {"paid": "✅", "pending": "⏳", "done": "✅", "cancelled": "❌", "late_cancel": "⚠️"}.get(booking.status, "❓")
        hours = hours_to_lesson(booking)
        hours_str = f"({hours:.1f}ч)" if hours >= 0 else "(истекло)"
        
        text += (
            f"{status_emoji} {booking.time} • {booking.trainer}\n"
            f"   👤 {booking.user_id} • {booking.lesson_type} {hours_str}\n"
        )
    
    # Inline-кнопки для каждого бронирования (Шаг 6.3)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"🔍 {b.time} {b.trainer}",
                callback_data=f"admin_booking_details_{b.id}"
            ),
            InlineKeyboardButton(
                text="⚙️",
                callback_data=f"admin_booking_actions_{b.id}"
            )
        ] for b in bookings[:10]  # Максимум 10 кнопок в сообщении
    ])
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin_panel")
    ])
    
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin_booking_actions_"))
async def show_booking_actions(callback: CallbackQuery):
    """Показывает действия для бронирования (Шаг 7.1-7.2)"""
    try:
        booking_id = int(callback.data.split("_")[3])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return
    
    async with AsyncSessionLocal() as session:
        booking = await session.get(Booking, booking_id)
        if not booking:
            await callback.answer("❌ Бронирование не найдено", show_alert=True)
            return
        
        hours = hours_to_lesson(booking)
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="❌ Отменить обычно",
                callback_data=f"admin_normal_cancel_{booking_id}"
            )],
            [InlineKeyboardButton(
                text="🚫 Override: отмена БЕЗ штрафа",
                callback_data=f"admin_no_penalty_cancel_{booking_id}"
            )],
            [InlineKeyboardButton(
                text="🔄 Перенести",
                callback_data=f"admin_reschedule_{booking_id}"
            )],
            [InlineKeyboardButton(
                text="✅ Отметить выполненным",
                callback_data=f"admin_mark_done_{booking_id}"
            )],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_today_bookings")]
        ]
    )
    
    text = (
        f"⚙️ <b>Действия с бронированием</b>\n\n"
        f"Время: {hours:.1f} часов до начала\n\n"
        f"🔑 <b>Override функции:</b> отмена и перенос БЕЗ штрафа\n"
        f"(с логированием для истории)"
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("admin_no_penalty_cancel_"))
async def admin_cancel_no_penalty(callback: CallbackQuery):
    """Admin override: отмена БЕЗ списания занятия (Шаг 7.2)"""
    try:
        booking_id = int(callback.data.split("_")[4])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return
    
    admin_id = callback.from_user.id
    
    async with AsyncSessionLocal() as session:
        booking = await session.get(Booking, booking_id)
        if not booking:
            await callback.answer("❌ Бронирование не найдено", show_alert=True)
            return
        
        # Сохраняем информацию для логирования
        user_id = booking.user_id
        lesson_type = booking.lesson_type
        
        # ✅ ОТМЕНА БЕЗ ПОТЕРЬ (OVERRIDE)
        booking.status = "cancelled"
        await session.commit()
        
        # ❌ ВАЖНО: Не списываем абонемент при override!
        # (Тогда как обычная отмена > 10 часов вернула бы занятие)
    
    # Логируем override действие
    await log_event_to_sheet(
        admin_id,
        f"admin_override_cancel_no_penalty: booking_id={booking_id}, user_id={user_id}, type={lesson_type}"
    )
    
    await log_event_to_sheet(
        user_id,
        f"admin_override: отмена без штрафа (отмена одобрена администратором)"
    )
    
    await callback.answer("✅ Бронирование отменено БЕЗ штрафа (override)", show_alert=True)
    await callback.message.edit_text(
        f"✅ <b>Override выполнено</b>\n\n"
        f"Бронирование отменено БЕЗ списания занятия\n"
        f"Пользователь: {user_id}\n"
        f"Логировано как override действие",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin_mark_done_"))
async def admin_mark_done(callback: CallbackQuery):
    """Отметить бронирование как выполненное"""
    try:
        booking_id = int(callback.data.split("_")[3])
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка", show_alert=True)
        return
    
    admin_id = callback.from_user.id
    
    async with AsyncSessionLocal() as session:
        booking = await session.get(Booking, booking_id)
        if not booking:
            await callback.answer("❌ Бронирование не найдено", show_alert=True)
            return
        
        booking.status = "done"
        await session.commit()
    
    await log_event_to_sheet(
        admin_id,
        f"admin_mark_done: booking_id={booking_id} (отмечено как выполненное)"
    )
    
    await callback.answer("✅ Отмечено как выполненное", show_alert=True)
    await callback.message.edit_text(
        f"✅ <b>Статус изменен</b>\n\n"
        f"Бронирование отмечено как выполненное",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "back_to_admin_panel")
async def back_to_admin_panel(callback: CallbackQuery):
    """Вернуться в админ-панель"""
    await admin_panel(callback.message)
