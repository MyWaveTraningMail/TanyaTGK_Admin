import logging
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from db.models import User, Booking, Subscription
from db.database import AsyncSessionLocal
from keyboards.booking import (
    trainers_keyboard, dates_keyboard, times_keyboard,
    payment_type_keyboard, confirm_booking_keyboard
)
from keyboards.lesson_type import lesson_type_keyboard
from services.google_sheets import (
    get_available_trainers, get_available_dates, get_available_times,
    log_event_to_sheet
)
from services.google_calendar import create_calendar_event
from services.yookassa import create_payment_link
from utils.constants import LESSON_TYPES, SBP_PHONE, PAYMENT_MESSAGE
from sqlalchemy import select

logger = logging.getLogger(__name__)
router = Router(name="booking_router")


class BookingStates(StatesGroup):
    choosing_lesson_type = State()    # Новое состояние: выбор типа занятия
    choosing_trainer = State()
    choosing_date = State()
    choosing_time = State()
    choosing_payment = State()
    confirming = State()


# ——— Начало записи ———
@router.message(F.text == "Записаться на занятие 🧘‍♀️")
async def start_booking(message: Message, state: FSMContext):
    """Начинает процесс бронирования с выбора типа занятия."""
    await state.set_state(BookingStates.choosing_lesson_type)
    await state.update_data(bookings=[])
    
    await log_event_to_sheet(message.from_user.id, "click: Записаться на занятие")
    
    await message.answer(
        "Какой тип занятия тебя интересует?",
        reply_markup=lesson_type_keyboard()
    )


# ——— Выбор типа занятия ———
@router.callback_query(BookingStates.choosing_lesson_type, F.data.startswith("lesson_"))
async def choose_lesson_type(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора типа занятия."""
    lesson_type = callback.data.split("_", 1)[1]  # trial, group_single, group_subscription, individual
    
    # Сохраняем тип занятия
    await state.update_data(lesson_type=lesson_type)
    
    # Проверяем, есть ли активный абонемент при выборе group_subscription
    if lesson_type == "group_subscription":
        telegram_id = callback.from_user.id
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Subscription).where(
                    (Subscription.user_id == telegram_id) &
                    (Subscription.classes_left > 0)
                )
            )
            active_sub = result.scalar_one_or_none()
        
        if not active_sub:
            await callback.answer("❌ У тебя нет активного абонемента!", show_alert=True)
            return
    
    # Переходим к выбору тренера
    trainers = await get_available_trainers()
    if not trainers:
        await callback.message.edit_text("😔 Сейчас нет свободных слотов. Попробуй позже!")
        return

    await state.set_state(BookingStates.choosing_trainer)
    await callback.message.edit_text(
        f"Тип: <b>{LESSON_TYPES.get(lesson_type, 'Неизвестный')}</b>\n\n"
        "Выбери тренера:",
        reply_markup=trainers_keyboard(trainers),
        parse_mode="HTML"
    )


# ——— Выбор тренера ———
@router.callback_query(BookingStates.choosing_trainer, F.data.startswith("trainer_"))
async def choose_trainer(callback: CallbackQuery, state: FSMContext):
    trainer = callback.data.split("_", 1)[1]
    await state.update_data(trainer=trainer)

    dates = await get_available_dates(trainer)
    if not dates:
        await callback.message.edit_text("Нет свободных дат у этого тренера 😔")
        return

    await state.set_state(BookingStates.choosing_date)
    await callback.message.edit_text(
        f"Тренер: <b>{trainer}</b>\nВыбери дату:",
        reply_markup=dates_keyboard(dates, trainer),
        parse_mode="HTML"
    )


# ——— Выбор даты ———
@router.callback_query(BookingStates.choosing_date, F.data.startswith("date_"))
async def choose_date(callback: CallbackQuery, state: FSMContext):
    _, trainer, pretty_date = callback.data.split("_", 2)
    data = await state.get_data()
    trainer = data.get("trainer", trainer)

    times = await get_available_times(trainer, pretty_date)
    if not times:
        await callback.message.edit_text("На эту дату нет свободного времени 😔")
        return

    await state.update_data(date=pretty_date, raw_date=pretty_date.split("|")[0].strip())
    await state.set_state(BookingStates.choosing_time)
    await callback.message.edit_text(
        f"Тренер: <b>{trainer}</b>\nДата: <b>{pretty_date.replace('|', ', ')}</b>\nВыбери время:",
        reply_markup=times_keyboard(times, trainer, pretty_date.split("|")[0].strip()),
        parse_mode="HTML"
    )


# ——— Выбор времени и цены ———
@router.callback_query(BookingStates.choosing_time, F.data.startswith("time_"))
async def choose_time(callback: CallbackQuery, state: FSMContext):
    _, trainer, date_str, time, price = callback.data.split("_", 4)
    price = int(price)

    await state.update_data(
        trainer=trainer,
        date=date_str,
        time=time,
        price=price,
        slot_price=price
    )

    await state.set_state(BookingStates.choosing_payment)
    await callback.message.edit_text(
        f"📅 {date_str} {datetime.strptime(date_str, '%d %B').strftime('%d.%m')}\n"
        f"🕐 {time} • {trainer}\n"
        f"💰 Стоимость: <b>{price} ₽</b>\n\n"
        "Как хочешь оплатить?",
        reply_markup=payment_type_keyboard(),
        parse_mode="HTML"
    )


# ——— Выбор типа оплаты ———
@router.callback_query(BookingStates.choosing_payment, F.data.in_({"pay_single", "pay_subscription"}))
async def choose_payment_type(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    payment_type = "single" if callback.data == "pay_single" else "subscription"

    await state.update_data(payment_type=payment_type)
    await state.set_state(BookingStates.confirming)

    text = (
        f"🔥 Подтверждение записи:\n\n"
        f"Тренер: <b>{data['trainer']}</b>\n"
        f"Дата: <b>{data['date'].replace('|', ', ')}</b>\n"
        f"Время: <b>{data['time']}</b>\n"
        f"Оплата: <b>{LESSON_TYPES.get(payment_type, 'Разовое')}</b>\n"
        f"Сумма: <b>{data['price']} ₽</b>\n\n"
        "Всё верно?"
    )

    await callback.message.edit_text(text, reply_markup=confirm_booking_keyboard(), parse_mode="HTML")


# ——— Финальное подтверждение ———
@router.callback_query(BookingStates.confirming, F.data == "confirm_booking")
async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback.from_user.id

    # Сохраняем в БД
    async with AsyncSessionLocal() as session:
        booking = Booking(
            user_id=user_id,
            trainer=data["trainer"],
            date=data["date"].split("|")[0].strip(),
            time=data["time"],
            price=data["price"],
            payment_type=data["payment_type"],
            lesson_type=data.get("lesson_type", "group_single"),  # Тип занятия
            status="pending"
        )
        session.add(booking)
        await session.commit()
        await session.refresh(booking)

    # Создаём событие в календаре тренера (заглушка, реализуем позже)
    await create_calendar_event(booking)

    # Обновляем или считаем по абонементу
    if data["payment_type"] == "subscription" and data.get("lesson_type") == "group_subscription":
        async with AsyncSessionLocal() as session:
            sub = await session.execute(
                select(Subscription).where(Subscription.user_id == user_id)
            )
            active_sub = sub.scalar_one_or_none()
            if active_sub and active_sub.classes_left > 0:
                active_sub.classes_left -= 1
                await session.commit()
        booking.status = "paid"
    else:
        booking.status = "pending"
    
    await session.commit()

    # Заглушка вместо оплаты через Yookassa (шаг 10.2)
    await callback.message.edit_text(
        f"✅ <b>Запись подтверждена!</b>\n\n"
        f"📅 {booking.date}\n"
        f"🕐 {booking.time}\n"
        f"👨‍🏫 {booking.trainer}\n\n"
        f"<b>Оплата:</b>\n{PAYMENT_MESSAGE}\n"
        f"После перевода кликни <code>Я оплатил(а)</code> или напиши админу! ✅",
        parse_mode="HTML"
    )

    await log_event_to_sheet(user_id, f"booking: {booking.trainer} {booking.date} {booking.time}")
    await state.clear()
