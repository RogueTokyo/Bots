#!/usr/bin/env python3
"""
Скрипт для запуска бота парсера Telegram каналов.
"""

from Парсер import main
import asyncio

if __name__ == "__main__":
    print("🚀 Запуск бота парсера Telegram каналов...")
    asyncio.run(main())
