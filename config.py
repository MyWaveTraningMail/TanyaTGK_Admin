import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
GOOGLE_SERVICE_ACCOUNT_FILE: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
GOOGLE_SHEET_ID: str = os.getenv("GOOGLE_SHEET_ID", "")

YOO_KASSA_SHOP_ID: str = os.getenv("YOO_KASSA_SHOP_ID", "")
YOO_KASSA_SECRET_KEY: str = os.getenv("YOO_KASSA_SECRET_KEY", "")

ADMIN_CHAT_ID: int = int(os.getenv("ADMIN_CHAT_ID", "0"))
TIMEZONE: str = os.getenv("TIMEZONE", "Europe/Moscow")

# Чаты тренеров
TRAINER_CHAT_IDS = {
    "Екатерина": os.getenv("TRAINER_EKATERINA_CHAT_ID"),
    "Анна": os.getenv("TRAINER_ANNA_CHAT_ID"),
    "Ольга": os.getenv("TRAINER_OLGA_CHAT_ID"),
}

BOT_USERNAME = "@PilatesReformerIzh_bot"
