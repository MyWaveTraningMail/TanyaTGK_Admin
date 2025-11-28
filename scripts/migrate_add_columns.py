#!/usr/bin/env python3
"""
Миграционный скрипт для добавления отсутствующих колонок в SQLite БД:
- users.last_inactivity_message_sent (DateTime NULLABLE)
- bookings.lesson_type (String, default 'group_single')

Скрипт безопасно проверяет наличие колонки через PRAGMA table_info
и выполняет ALTER TABLE ADD COLUMN только если колонки нет.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path("pilates_bot.db")


def has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Проверяет наличие колонки в таблице"""
    cur = conn.execute(f"PRAGMA table_info({table});")
    cols = [row[1] for row in cur.fetchall()]
    return column in cols


def main():
    """Выполняет миграцию"""
    if not DB_PATH.exists():
        print(f"❌ БД '{DB_PATH}' не найдена.")
        print("💡 Запустите бота один раз, чтобы создать БД: python main.py")
        return False

    conn = sqlite3.connect(DB_PATH)
    try:
        print("🔍 Проверка колонок...\n")
        
        # users.last_inactivity_message_sent
        if not has_column(conn, "users", "last_inactivity_message_sent"):
            print("📝 Добавляю: users.last_inactivity_message_sent")
            conn.execute(
                "ALTER TABLE users ADD COLUMN last_inactivity_message_sent TIMESTAMP"
            )
            print("✅ Готово!\n")
        else:
            print("✓ users.last_inactivity_message_sent уже существует\n")

        # bookings.lesson_type
        if not has_column(conn, "bookings", "lesson_type"):
            print("📝 Добавляю: bookings.lesson_type")
            conn.execute(
                "ALTER TABLE bookings ADD COLUMN lesson_type TEXT DEFAULT 'group_single'"
            )
            print("✅ Готово!\n")
        else:
            print("✓ bookings.lesson_type уже существует\n")

        conn.commit()
        print("🎉 Миграция завершена успешно!")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Ошибка при миграции: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    print("🚀 Запуск миграции БД Pilates Reformer\n")
    success = main()
    if success:
        print("\n✨ Теперь можете запустить бота: python main.py")
    else:
        print("\n⚠️  Миграция не удалась")


if __name__ == '__main__':
    main()
