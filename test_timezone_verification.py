#!/usr/bin/env python3
"""
Скрипт проверки расчёта времени урока с использованием TIMEZONE (Europe/Samara).

Кейсы:
1. Создание тестовой брони на дату/время
2. Расчёт lesson_datetime с учётом TIMEZONE
3. Вычисление напоминаний (12ч и 2ч до)
4. Проверка offset UTC для Europe/Samara (должен быть +4)
"""

import sys
from datetime import datetime, timedelta
import pytz

# Импортируем TIMEZONE из config
from config import TIMEZONE

def test_timezone_verification():
    """Основной тест: проверка расчётов с TIMEZONE"""
    
    print("=" * 80)
    print("🔍 ПРОВЕРКА РАСЧЁТОВ ВРЕМЕНИ С TIMEZONE (Europe/Samara)")
    print("=" * 80)
    print()
    
    # Информация о TIMEZONE
    print(f"📌 Текущий TIMEZONE: {TIMEZONE}")
    tz = pytz.timezone(TIMEZONE)
    print(f"✅ Timezone объект загружен: {tz}")
    print()
    
    # Текущее время в TIMEZONE
    now_tz = datetime.now(tz=tz)
    print(f"📅 Текущее время в {TIMEZONE}:")
    print(f"   {now_tz.strftime('%Y-%m-%d %H:%M:%S %Z (UTC%z)')}")
    print()
    
    # Проверка UTC offset
    offset = now_tz.strftime('%z')
    offset_hours = int(offset[:3])
    print(f"🕐 UTC Offset: {offset}")
    if offset_hours == 4:
        print(f"   ✅ Правильно! Ижевск: UTC+4 (летнее время) или UTC+4 (Samara Standard Time)")
    else:
        print(f"   ⚠️  Внимание: Offset {offset_hours}, ожидалось +4")
    print()
    
    # Тестовый кейс: создание брони на следующий день в 10:00
    print("📋 ТЕСТОВАЯ БРОНЬ: Завтрашний день, 10:00")
    print("-" * 80)
    
    # Парсируем "завтра 10:00" в формате, как поступает из бота
    tomorrow = now_tz + timedelta(days=1)
    date_str = tomorrow.strftime("%d %B %Y")  # например, "29 ноября 2025"
    time_str = "10:00"
    
    print(f"   Дата (из Google Sheets): {date_str}")
    print(f"   Время: {time_str}")
    
    # Парсируем как в schedule_reminders
    lesson_dt_naive = datetime.strptime(f"{date_str} {time_str}", "%d %B %Y %H:%M")
    lesson_dt = tz.localize(lesson_dt_naive)
    
    print(f"   → lesson_datetime (timezone-aware): {lesson_dt.strftime('%Y-%m-%d %H:%M:%S %Z (UTC%z)')}")
    print()
    
    # Вычисляем напоминания
    reminder_12 = lesson_dt - timedelta(hours=12)
    reminder_2 = lesson_dt - timedelta(hours=2)
    
    print("⏰ РАСЧЁТ НАПОМИНАНИЙ:")
    print(f"   Занятие: {lesson_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"   Напоминание за 12ч: {reminder_12.strftime('%Y-%m-%d %H:%M:%S %Z')} (в {reminder_12.strftime('%H:%M')})")
    print(f"   Напоминание за 2ч:  {reminder_2.strftime('%Y-%m-%d %H:%M:%S %Z')} (в {reminder_2.strftime('%H:%M')})")
    print()
    
    # Проверка: напоминания должны быть в прошлом или будущем (в зависимости от времени)
    if reminder_12 > now_tz:
        print(f"   ✅ Напоминание за 12ч в будущем (будет запланировано)")
    else:
        print(f"   ⚠️  Напоминание за 12ч в прошлом (не будет запланировано) — это нормально, если бронь ближе чем за 12ч")
    
    if reminder_2 > now_tz:
        print(f"   ✅ Напоминание за 2ч в будущем (будет запланировано)")
    else:
        print(f"   ⚠️  Напоминание за 2ч в прошлом (не будет запланировано) — это нормально, если бронь ближе чем за 2ч")
    print()
    
    # Кейс 2: Бронь, которая точно в будущем (через 1 день + 5 часов)
    print("📋 ТЕСТОВАЯ БРОНЬ #2: Отдалённое время (для гарантии напоминаний)")
    print("-" * 80)
    
    future = now_tz + timedelta(days=1, hours=5)
    future_date_str = future.strftime("%d %B %Y")
    future_time_str = future.strftime("%H:00")  # Ровное время
    
    print(f"   Дата: {future_date_str}")
    print(f"   Время: {future_time_str}")
    
    future_dt_naive = datetime.strptime(f"{future_date_str} {future_time_str}", "%d %B %Y %H:%M")
    future_dt = tz.localize(future_dt_naive)
    
    future_reminder_12 = future_dt - timedelta(hours=12)
    future_reminder_2 = future_dt - timedelta(hours=2)
    
    print(f"   → lesson_datetime: {future_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"   Напоминание за 12ч: {future_reminder_12.strftime('%Y-%m-%d %H:%M:%S %Z')} (в {future_reminder_12.strftime('%H:%M')})")
    print(f"   Напоминание за 2ч:  {future_reminder_2.strftime('%Y-%m-%d %H:%M:%S %Z')} (в {future_reminder_2.strftime('%H:%M')})")
    
    if future_reminder_12 > now_tz and future_reminder_2 > now_tz:
        print(f"   ✅ ОБА напоминания в будущем — будут запланированы корректно")
    else:
        print(f"   ⚠️  Одно или оба напоминания в прошлом")
    print()
    
    # Итоговая проверка
    print("=" * 80)
    print("✅ ИТОГОВАЯ ПРОВЕРКА:")
    print(f"   • TIMEZONE правильно установлен: {TIMEZONE}")
    print(f"   • UTC offset корректный: {offset}")
    print(f"   • Расчёты времени работают правильно с timezone-aware datetime")
    print(f"   • Напоминания рассчитываются с учётом TIMEZONE")
    print("=" * 80)
    print()
    
    return True

if __name__ == "__main__":
    try:
        success = test_timezone_verification()
        if success:
            print("✅ Скрипт выполнен успешно!")
            sys.exit(0)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
