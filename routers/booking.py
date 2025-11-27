import logging
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from db.models import User, Booking
from db.database import AsyncSessionLocal
from keyboards.booking import (
    trainers_keyboard, dates_keyboard, times_keyboard,
    payment_type_keyboard, confirm_booking_keyboard
)
from services.google_sheets import (
    get_available_trainers, get_available_dates, get_available_times
)
from services.google_calendar import create_calendar_event
from services.yookassa import create_payment_link
from utils.constants import LESSON_TYPES

logger = logging.getLogger(__name__)
router = Router(name="booking_router")


class BookingStates(StatesGroup):
    choosing_trainer = State()
    choosing_date = State()
    choosing_time = State()
    choosing_payment = State()
    confirming = State()


# ——— Начало записи ———
@router.message(F.text == "Записаться на занятие 🧘‍♀️")
async def start_booking(message: Message, state: FSMContext):
    trainers = await get_available_trainers()
    if not trainers:
        await message.answer("😔 Сейчас нет свободных слотов. Попробуй позже!")
        return

    await state.set_state(BookingStates.choosing_trainer)
    await state.update_data(bookings=[])
    await message.answer(
        "Выбери тренера:",
        reply_markup=trainers_keyboard(trainers)
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
            status="pending"
        )
        session.add(booking)
        await session.commit()
        await session.refresh(booking)

    # Создаём событие в календаре тренера (заглушка, реализуем позже)
    await create_calendar_event(booking)

    if data["payment_type"] == "single":
        payment_url, payment_id = await create_payment_link(
            amount=data["price"],
            description=f"Запись на {data['trainer']} {data['date']} {data['time']}",
            user_id=user_id,
            booking_id=booking.id
        )
        await callback.message.edit_text(
            f"✅ Запись создана!\nОсталось только оплатить:\n\n{payment_url}",
            disable_web_page_preview=True
        )
    else:
        await callback.message.edit_text(
            "✅ Запись создана и оплачена абонементом!\nСкоро пришлю напоминание 💪"
        )

    await state.clear()
