import logging
from datetime import datetime, timedelta
from typing import List, Dict

import gspread
from google.oauth2.service_account import Credentials

from config import GOOGLE_SERVICE_ACCOUNT_FILE, GOOGLE_SHEET_ID

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

MONTHS_RU = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}

WEEKDAYS_RU_SHORT = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]


def _get_client():
    creds = Credentials.from_service_account_file(GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return gspread.authorize(creds)


async def get_available_trainers() -> List[str]:
    """Возвращает список тренеров у которых есть хотя бы одно свободное место в ближайшие 30 дней"""
    try:
        client = _get_client()
        sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet("Schedule")
        records = sheet.get_all_records()
        trainers = {
            row["Тренер"] for row in records
            if int(row.get("Свободно", 0)) > 0
        }
        return sorted(list(trainers))
    except Exception as e:
        logger.error(f"Ошибка чтения тренеров из Google Sheets: {e}")
        return []


async def get_available_dates(trainer: str, days_ahead: int = 30) -> List[str]:
    """Возвращает список дат в формате '15 марта|пт' для красивых кнопок"""
    try:
        client = _get_client()
        sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet("Schedule")
        records = sheet.get_all_records()

        result = []
        today = datetime.today().date()
        for row in records:
            if row["Тренер"] != trainer:
                continue
            try:
                slot_date = datetime.strptime(row["Дата"], "%d.%m.%Y").date()
            except:
                continue

            if today <= slot_date <= today + timedelta(days=days_ahead):
                if int(row.get("Свободно", 0)) > 0:
                    day = slot_date.day
                    month_name = MONTHS_RU[slot_date.month]
                    weekday = WEEKDAYS_RU_SHORT[slot_date.weekday()]
                    pretty_date = f"{day} {month_name}|{weekday}"
                    result.append(pretty_date)

        return sorted(list(set(result)), key=lambda x: datetime.strptime(x.split("|")[0], "%d %B"))
    except Exception as e:
        logger.error(f"Ошибка получения дат: {e}")
        return []


async def get_available_times(trainer: str, date_str: str) -> List[Dict]:
    """
    date_str — в формате "15 марта"
    Возвращает список словарей: {'time': '10:00', 'free': 2, 'price': 1800, 'row': 5}
    """
    try:
        client = _get_client()
        sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet("Schedule")
        all_records = sheet.get_all_records()

        target_day = int(date_str.split()[0])
        target_month = list(MONTHS_RU.values()).index(date_str.split()[1]) + 1

        result = []
        for idx, row in enumerate(all_records, start=2):  # +2 потому что заголовок + индексация gspread
            if row["Тренер"] != trainer:
                continue
            try:
                row_date = datetime.strptime(row["Дата"], "%d.%m.%Y")
                if row_date.day == target_day and row_date.month == target_month:
                    free = int(row.get("Свободно", 0))
                    if free > 0:
                        result.append({
                            "time": row["Время"],
                            "free": free,
                            "price": int(row["Цена"]),
                            "row_index": idx
                        })
            except:
                continue
        return result
    except Exception as e:
        logger.error(f"Ошибка получения времени: {e}")
        return []


async def get_faq_answers() -> list[tuple[str, str]]:
    try:
        client = _get_client()
        sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet("FAQ")
        records = sheet.get_all_records()
        return [(row["Вопрос"], row["Ответ"]) for row in records if row.get("Вопрос") and row.get("Ответ")]
    except Exception as e:
        logger.error(f"Ошибка чтения FAQ: {e}")
        return []


async def update_free_slots(row_index: int, delta: int) -> bool:
    """
    Изменяет количество свободных мест в слоте на +/- delta.
    
    Args:
        row_index: Номер строки в листе Schedule (1-based индексация для Sheets API)
        delta: Дельта изменения (-1 при броне, +1 при отмене)
    
    Returns:
        True, если успешно, False в случае ошибки
    """
    try:
        client = _get_client()
        sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet("Schedule")
        
        # Получаем текущее значение
        cell = sheet.cell(row_index, col=5)  # Столбец "Свободно" (примерно 5-й)
        current = int(cell.value or 0)
        new_value = max(0, current + delta)
        
        # Обновляем значение
        sheet.update_cell(row_index, 5, new_value)
        logger.info(f"Обновлены свободные места: строка {row_index}, было {current}, стало {new_value}")
        return True
    except Exception as e:
        logger.error(f"Ошибка обновления свободных мест: {e}")
        return False


async def log_event_to_sheet(telegram_id: int, action_text: str) -> bool:
    """
    Логирует действие пользователя в лист Events.
    
    Args:
        telegram_id: Telegram ID пользователя
        action_text: Текст действия (например, "click: Записаться на занятие")
    
    Returns:
        True, если успешно, False в случае ошибки
    """
    try:
        client = _get_client()
        sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet("Events")
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Добавляем новую строку: Telegram ID, Время, Действие
        sheet.append_row([telegram_id, timestamp, action_text])
        logger.debug(f"Логировано действие: {telegram_id} — {action_text}")
        return True
    except Exception as e:
        logger.error(f"Ошибка логирования действия: {e}")
        return False
