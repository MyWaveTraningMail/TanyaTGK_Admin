#!/usr/bin/env python3
"""
Скрипт проверки конфигурации Google Sheets для бота Pilates Reformer.

Использование:
    python check_google_sheets_config.py
"""

import sys
from pathlib import Path

# Добавляем корневую папку в path
sys.path.insert(0, str(Path(__file__).parent))

from config import GOOGLE_SHEET_ID, GOOGLE_SERVICE_ACCOUNT_FILE


def check_config():
    """Проверяет конфигурацию Google Sheets."""
    
    print("\n" + "="*70)
    print("🔍 ПРОВЕРКА КОНФИГУРАЦИИ GOOGLE SHEETS")
    print("="*70 + "\n")
    
    # Проверка 1: GOOGLE_SHEET_ID
    print("1️⃣  Проверка GOOGLE_SHEET_ID:")
    if not GOOGLE_SHEET_ID:
        print("   ❌ GOOGLE_SHEET_ID не установлен (пустая строка)")
        print("   📝 Установите реальный ID в файле .env")
        return False
    
    if GOOGLE_SHEET_ID.startswith("1aBcDeFgHiJkLmNoPqRsTuVwXyZ"):
        print(f"   ❌ GOOGLE_SHEET_ID содержит ТЕСТОВЫЙ ID: {GOOGLE_SHEET_ID}")
        print("   📝 Замените на реальный ID из вашей Google Sheets таблицы")
        print("   📄 Инструкция: см. файл SETUP_GOOGLE_SHEETS.md")
        return False
    else:
        print(f"   ✅ GOOGLE_SHEET_ID установлен: {GOOGLE_SHEET_ID[:30]}...")
    
    # Проверка 2: service_account.json
    print("\n2️⃣  Проверка файла сервисного аккаунта:")
    service_file = Path(GOOGLE_SERVICE_ACCOUNT_FILE)
    
    if not service_file.exists():
        print(f"   ❌ Файл не найден: {GOOGLE_SERVICE_ACCOUNT_FILE}")
        print("   📝 Убедитесь, что файл находится в корне проекта")
        return False
    else:
        print(f"   ✅ Файл найден: {GOOGLE_SERVICE_ACCOUNT_FILE}")
    
    # Проверка 3: Попытка подключения
    print("\n3️⃣  Попытка подключения к Google Sheets:")
    try:
        from services.google_sheets import _get_client
        client = _get_client()
        print("   ✅ Клиент Google Sheets инициализирован успешно")
    except FileNotFoundError as e:
        print(f"   ❌ Ошибка: Файл сервисного аккаунта не найден")
        print(f"   📝 {e}")
        return False
    except Exception as e:
        print(f"   ⚠️  Ошибка инициализации: {e}")
        print("   📝 Проверьте файл service_account.json и права доступа")
        return False
    
    # Проверка 4: Попытка открыть таблицу
    print("\n4️⃣  Проверка доступа к Google Sheets таблице:")
    try:
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
        print(f"   ✅ Таблица найдена: '{spreadsheet.title}'")
        
        # Список листов
        worksheets = [ws.title for ws in spreadsheet.worksheets()]
        print(f"   📋 Доступные листы: {', '.join(worksheets)}")
        
        # Проверка необходимых листов
        required_sheets = ["Schedule", "FAQ", "Events"]
        missing = [s for s in required_sheets if s not in worksheets]
        
        if missing:
            print(f"   ⚠️  Отсутствуют листы: {', '.join(missing)}")
            print(f"   📝 Создайте следующие листы в Google Sheets:")
            for sheet in missing:
                print(f"      - {sheet}")
            return False
        else:
            print(f"   ✅ Все необходимые листы присутствуют")
        
    except Exception as e:
        print(f"   ❌ Ошибка доступа к таблице: {e}")
        print("   📝 Проверьте:")
        print("      1. GOOGLE_SHEET_ID корректен (скопирован полностью)")
        print("      2. Таблица существует")
        print("      3. Сервисный аккаунт имеет доступ (Редактор)")
        return False
    
    # Всё хорошо
    print("\n" + "="*70)
    print("✅ КОНФИГУРАЦИЯ УСПЕШНА!")
    print("="*70 + "\n")
    print("Бот готов к работе с Google Sheets.\n")
    return True


if __name__ == "__main__":
    success = check_config()
    sys.exit(0 if success else 1)
