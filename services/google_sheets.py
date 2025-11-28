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


def _open_worksheet(title: str):
    """Возвращает worksheet по названию листа, с подробными логами об ошибках.

    Бросает исключение дальше, чтобы вызывающий код мог обработать ошибку.
    """
    try:
        client = _get_client()
    except FileNotFoundError as e:
        logger.error(f"Файл сервисного аккаунта не найден: {GOOGLE_SERVICE_ACCOUNT_FILE} — {e}")
        raise
    except Exception as e:
        logger.error(f"Ошибка инициализации клиента Google Sheets: {e}")
        raise

    try:
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
    except gspread.exceptions.SpreadsheetNotFound:
        logger.error(
            f"Google Sheet с ID '{GOOGLE_SHEET_ID}' не найден. Проверьте переменную GOOGLE_SHEET_ID и доступ сервисного аккаунта."
        )
        raise
    except gspread.exceptions.APIError as e:
        logger.error(
            f"API Error при доступе к Google Sheets: {e}. Проверьте права доступа сервисного аккаунта и что sheet id корректен."
        )
        raise

    try:
        sheet = spreadsheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        logger.error(f"Лист с названием '{title}' не найден в таблице {GOOGLE_SHEET_ID}.")
        raise

    return sheet


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


async def get_available_times(trainer: str, date_str: str, lesson_type: str = None) -> List[Dict]:
    """
    date_str — в формате "15 марта"
    lesson_type — опционально фильтровать по типу занятия (trial, group_single, group_subscription, individual)
    
    Возвращает список словарей: {
        'time': '10:00',
        'free': 2,
        'price': 1800,
        'lesson_type': 'individual',
        'row_index': 5
    }
    """
    try:
        client = _get_client()
        sheet = _open_worksheet("Schedule")
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
                    
                    # Фильтруем по типу занятия если указан
                    row_lesson_type = row.get("Типтренировки", "").lower()
                    if lesson_type and row_lesson_type != lesson_type.lower():
                        continue
                    
                    if free > 0:
                        result.append({
                            "time": row["Время"],
                            "free": free,
                            "price": int(row.get("Цена", 0)),
                            "lesson_type": row_lesson_type or "group_single",
                            "row_index": idx
                        })
            except ValueError:
                continue
        return result
    except Exception as e:
        logger.error(f"Ошибка получения времени: {e}")
        return []


async def get_faq_answers() -> list[tuple[str, str]]:
    try:
        client = _get_client()
        sheet = _open_worksheet("FAQ")
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
        sheet = _open_worksheet("Schedule")
        
        # Находим столбец "Свободно"
        headers = sheet.row_values(1)
        free_col = headers.index("Свободно") + 1 if "Свободно" in headers else 5
        
        # Получаем текущее значение
        cell = sheet.cell(row_index, col=free_col)
        current = int(cell.value or 0)
        new_value = max(0, current + delta)
        
        # Обновляем значение
        sheet.update_cell(row_index, free_col, new_value)
        logger.info(f"Обновлены свободные места: строка {row_index}, было {current}, стало {new_value}")
        return True
    except Exception as e:
        logger.error(f"Ошибка обновления свободных мест: {e}")
        return False


async def get_lesson_type_from_sheet(trainer: str, date_str: str, time_str: str) -> str:
    """
    Получает тип занятия из Google Sheets для заданного слота.
    
    Args:
        trainer: Имя тренера
        date_str: Дата в формате "15 марта"
        time_str: Время в формате "10:00"
    
    Returns:
        Тип занятия (trial, group_single, group_subscription, individual) или "group_single" по умолчанию
    """
    try:
        client = _get_client()
        sheet = _open_worksheet("Schedule")
        all_records = sheet.get_all_records()

        target_day = int(date_str.split()[0])
        target_month = list(MONTHS_RU.values()).index(date_str.split()[1]) + 1

        for row in all_records:
            if row.get("Тренер") != trainer or row.get("Время") != time_str:
                continue
            try:
                row_date = datetime.strptime(row["Дата"], "%d.%m.%Y")
                if row_date.day == target_day and row_date.month == target_month:
                    lesson_type = row.get("Типтренировки", "group_single").lower()
                    return lesson_type if lesson_type in ["trial", "group_single", "group_subscription", "individual"] else "group_single"
            except ValueError:
                continue
        
        return "group_single"
    except Exception as e:
        logger.error(f"Ошибка получения типа занятия: {e}")
        return "group_single"


async def update_lesson_type(row_index: int, lesson_type: str) -> bool:
    """
    Обновляет тип занятия в Google Sheets.
    
    Args:
        row_index: Номер строки
        lesson_type: Тип занятия (trial, group_single, group_subscription, individual)
    
    Returns:
        True, если успешно
    """
    try:
        client = _get_client()
        sheet = _open_worksheet("Schedule")
        
        headers = sheet.row_values(1)
        lesson_type_col = headers.index("Типтренировки") + 1 if "Типтренировки" in headers else 6
        
        sheet.update_cell(row_index, lesson_type_col, lesson_type)
        logger.info(f"Обновлен тип занятия: строка {row_index} → {lesson_type}")
        return True
    except Exception as e:
        logger.error(f"Ошибка обновления типа занятия: {e}")
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
        sheet = _open_worksheet("Events")
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Добавляем новую строку: Telegram ID, Время, Действие
        sheet.append_row([telegram_id, timestamp, action_text])
        logger.debug(f"Логировано действие: {telegram_id} — {action_text}")
        return True
    except Exception as e:
        logger.error(f"Ошибка логирования действия: {e}")
        return False
