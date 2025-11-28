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
    # Проверяем валидность GOOGLE_SHEET_ID
    if not GOOGLE_SHEET_ID or GOOGLE_SHEET_ID.startswith("1aBcDeFgHiJkLmNoPqRsTuVwXyZ"):
        logger.error(
            f"⚠️ КРИТИЧЕСКАЯ ОШИБКА: GOOGLE_SHEET_ID содержит тестовый ID '{GOOGLE_SHEET_ID}'.\n"
            f"Для использования бота необходимо:\n"
            f"1. Создать Google Sheet: https://sheets.google.com/create\n"
            f"2. Скопировать ID из URL (находится между /d/ и /edit)\n"
            f"3. Установить GOOGLE_SHEET_ID в .env файле\n"
            f"4. Поделиться доступом к таблице с сервисным аккаунтом"
        )
        raise ValueError(
            f"GOOGLE_SHEET_ID не установлен корректно. Это тестовый ID. "
            f"Установите реальный ID из вашей Google Sheets таблицы в файл .env"
        )
    
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
        if not GOOGLE_SHEET_ID or GOOGLE_SHEET_ID.startswith("1aBcDeFgHiJkLmNoPqRsTuVwXyZ"):
            logger.debug("Google Sheets недоступен - используются тестовые данные")
            return ["Екатерина", "Анна", "Ольга"]
        
        client = _get_client()
        sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet("Schedule")
        records = sheet.get_all_records()
        trainers = {
            row["Тренер"] for row in records
            if int(row.get("Свободно", 0)) > 0
        }
        return sorted(list(trainers)) if trainers else ["Екатерина", "Анна", "Ольга"]
    except ValueError as e:
        logger.debug(f"Google Sheets недоступен - используются тестовые данные: {e}")
        return ["Екатерина", "Анна", "Ольга"]
    except Exception as e:
        logger.error(f"Ошибка чтения тренеров из Google Sheets: {e}")
        return ["Екатерина", "Анна", "Ольга"]


async def get_available_dates(trainer: str, days_ahead: int = 30) -> List[str]:
    """Возвращает список дат в формате '15 марта|пт' для красивых кнопок"""
    try:
        if not GOOGLE_SHEET_ID or GOOGLE_SHEET_ID.startswith("1aBcDeFgHiJkLmNoPqRsTuVwXyZ"):
            logger.debug(f"Google Sheets недоступен - генерируем тестовые даты для {trainer}")
            # Генерируем тестовые даты (сегодня и на 7 дней вперед)
            result = []
            today = datetime.today().date()
            for i in range(7):
                date = today + timedelta(days=i)
                day = date.day
                month_name = MONTHS_RU[date.month]
                weekday = WEEKDAYS_RU_SHORT[date.weekday()]
                pretty_date = f"{day} {month_name}|{weekday}"
                result.append(pretty_date)
            logger.debug(f"Возвращаем {len(result)} тестовых дат: {result}")
            return result
        
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

        if result:
            return sorted(list(set(result)), key=lambda x: datetime.strptime(x.split("|")[0], "%d %B"))
        else:
            # Если нет данных в Google Sheets, возвращаем тестовые
            logger.debug("Google Sheets нет данных - возвращаем тестовые даты")
            result = []
            today = datetime.today().date()
            for i in range(7):
                date = today + timedelta(days=i)
                day = date.day
                month_name = MONTHS_RU[date.month]
                weekday = WEEKDAYS_RU_SHORT[date.weekday()]
                pretty_date = f"{day} {month_name}|{weekday}"
                result.append(pretty_date)
            return result
    except ValueError as e:
        logger.debug(f"Google Sheets недоступен - генерируем тестовые даты: {e}")
        # Генерируем тестовые даты
        result = []
        today = datetime.today().date()
        for i in range(7):
            date = today + timedelta(days=i)
            day = date.day
            month_name = MONTHS_RU[date.month]
            weekday = WEEKDAYS_RU_SHORT[date.weekday()]
            pretty_date = f"{day} {month_name}|{weekday}"
            result.append(pretty_date)
        return result
    except Exception as e:
        logger.error(f"Ошибка получения дат: {e}")
        # Генерируем тестовые даты
        result = []
        today = datetime.today().date()
        for i in range(7):
            date = today + timedelta(days=i)
            day = date.day
            month_name = MONTHS_RU[date.month]
            weekday = WEEKDAYS_RU_SHORT[date.weekday()]
            pretty_date = f"{day} {month_name}|{weekday}"
            result.append(pretty_date)
        return result


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
    
    Режим: 9:00-20:00, каждый час (1-часовые слоты)
    """
    try:
        if not GOOGLE_SHEET_ID or GOOGLE_SHEET_ID.startswith("1aBcDeFgHiJkLmNoPqRsTuVwXyZ"):
            logger.debug(f"Google Sheets недоступен - генерируем тестовые времена 9:00-20:00 для {trainer}")
            # Генерируем полное расписание 9:00-20:00 (каждый час)
            # Групповые занятия: 9:00-12:00, 14:00-20:00
            # Индивидуальные: 15:00-20:00
            test_times = []
            
            # Групповые занятия (1000₽, 3-5 свободных мест)
            group_slots = ["09:00", "10:00", "11:00", "12:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00"]
            for idx, time_slot in enumerate(group_slots, start=2):
                test_times.append({
                    "time": time_slot,
                    "free": 3 if idx % 2 == 0 else 2,
                    "price": 1000,
                    "lesson_type": "group_single",
                    "row_index": idx
                })
            
            # Индивидуальные занятия (1800₽, 1-2 свободных места)
            individual_slots = ["15:00", "16:00", "17:00", "18:00", "19:00", "20:00"]
            for idx, time_slot in enumerate(individual_slots, start=15):
                test_times.append({
                    "time": time_slot,
                    "free": 2 if idx % 2 == 0 else 1,
                    "price": 1800,
                    "lesson_type": "individual",
                    "row_index": idx
                })
            
            # Фильтруем по типу если нужно
            if lesson_type:
                filtered = [t for t in test_times if t["lesson_type"] == lesson_type]
                logger.debug(f"Возвращаем {len(filtered)} тестовых слотов для {lesson_type}")
                return filtered
            
            logger.debug(f"Возвращаем {len(test_times)} тестовых слотов")
            return test_times
        
        client = _get_client()
        sheet = _open_worksheet("Schedule")
        all_records = sheet.get_all_records()

        target_day = int(date_str.split()[0])
        target_month = list(MONTHS_RU.values()).index(date_str.split()[1]) + 1

        result = []
        for idx, row in enumerate(all_records, start=2):
            if row["Тренер"] != trainer:
                continue
            try:
                row_date = datetime.strptime(row["Дата"], "%d.%m.%Y")
                if row_date.day == target_day and row_date.month == target_month:
                    free = int(row.get("Свободно", 0))
                    
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
        
        if result:
            return result
        else:
            # Если нет данных в Google Sheets, возвращаем тестовые 9:00-20:00
            logger.debug(f"Google Sheets нет данных для {trainer} на {date_str} - возвращаем тестовые слоты")
            test_times = []
            
            group_slots = ["09:00", "10:00", "11:00", "12:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00"]
            for idx, time_slot in enumerate(group_slots, start=2):
                test_times.append({
                    "time": time_slot,
                    "free": 3 if idx % 2 == 0 else 2,
                    "price": 1000,
                    "lesson_type": "group_single",
                    "row_index": idx
                })
            
            if lesson_type:
                return [t for t in test_times if t["lesson_type"] == lesson_type]
            return test_times
    except ValueError as e:
        logger.debug(f"Google Sheets недоступен - генерируем тестовые времена: {e}")
        test_times = []
        
        group_slots = ["09:00", "10:00", "11:00", "12:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00"]
        for idx, time_slot in enumerate(group_slots, start=2):
            test_times.append({
                "time": time_slot,
                "free": 3 if idx % 2 == 0 else 2,
                "price": 1000,
                "lesson_type": "group_single",
                "row_index": idx
            })
        
        if lesson_type:
            return [t for t in test_times if t["lesson_type"] == lesson_type]
        return test_times
    except Exception as e:
        logger.error(f"Ошибка получения времени: {e}")
        # Возвращаем основные слоты
        return [
            {"time": "09:00", "free": 3, "price": 1000, "lesson_type": "group_single", "row_index": 2},
            {"time": "10:00", "free": 2, "price": 1000, "lesson_type": "group_single", "row_index": 3},
            {"time": "15:00", "free": 2, "price": 1800, "lesson_type": "individual", "row_index": 5},
            {"time": "16:00", "free": 1, "price": 1800, "lesson_type": "individual", "row_index": 6},
        ]
        return test_times
    except Exception as e:
        logger.error(f"Ошибка получения времени: {e}")
        return [
            {"time": "09:00", "free": 3, "price": 1000, "lesson_type": "group_single", "row_index": 2},
            {"time": "15:00", "free": 2, "price": 1800, "lesson_type": "individual", "row_index": 5},
        ]


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
        if not GOOGLE_SHEET_ID or GOOGLE_SHEET_ID.startswith("1aBcDeFgHiJkLmNoPqRsTuVwXyZ"):
            logger.debug(f"Логирование пропущено: GOOGLE_SHEET_ID не установлен корректно (тестовый ID)")
            return False
        
        client = _get_client()
        sheet = _open_worksheet("Events")
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Добавляем новую строку: Telegram ID, Время, Действие
        sheet.append_row([telegram_id, timestamp, action_text])
        logger.debug(f"Логировано действие: {telegram_id} — {action_text}")
        return True
    except ValueError as e:
        logger.debug(f"⚠️ Google Sheets недоступен: {e}")
        return False
    except Exception as e:
        logger.debug(f"Ошибка логирования действия (некритично): {e}")
        return False  # Логирование не должно ломать основной функционал
