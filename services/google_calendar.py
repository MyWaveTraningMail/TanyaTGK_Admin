import logging
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from config import GOOGLE_SERVICE_ACCOUNT_FILE, TIMEZONE

logger = logging.getLogger(__name__)
SCOPES = ['https://www.googleapis.com/auth/calendar']

def _get_calendar_service():
    creds = Credentials.from_service_account_file(GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('calendar', 'v3', credentials=creds)


async def create_calendar_event(booking) -> bool:
    """
    Создаёт событие в Google Calendar конкретного тренера
    booking — объект модели Booking из БД
    """
    try:
        # Находим Calendar ID тренера из Google Sheets (мы сохраним его при чтении слота)
        # Временно — заглушка: нужно будет доработать при интеграции с Schedule
        trainer_to_calendar = {
            "Екатерина": "c_ekaterina@example.com",
            "Анна": "c_anna@example.com",
            "Ольга": "c_olga@example.com",
        }
        calendar_id = trainer_to_calendar.get(booking.trainer)
        if not calendar_id:
            logger.warning(f"Calendar ID не найден для тренера {booking.trainer}")
            return False

        service = _get_calendar_service()

        event_date = datetime.strptime(f"{booking.date} 2025", "%d %B %Y").strftime("%Y-%m-%d")
        start_time = datetime.strptime(f"{event_date} {booking.time}", "%Y-%m-%d %H:%M")
        end_time = start_time + timedelta(hours=1)

        event = {
            'summary': f'Пилатес • {booking.user.full_name or "Клиент"}',
            'description': f'Telegram: @{booking.user.telegram_id}\nОплата: {booking.payment_type}',
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': TIMEZONE,
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': TIMEZONE,
            },
            'attendees': [],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 120},
                    {'method': 'popup', 'minutes': 30},
                ],
            },
        }

        service.events().insert(calendarId=calendar_id, body=event).execute()
        logger.info(f"Событие создано в календаре {booking.trainer}: {booking.date} {booking.time}")
        return True

    except Exception as e:
        logger.error(f"Ошибка создания события в Google Calendar: {e}")
        return False
