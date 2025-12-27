#!/usr/bin/env python3
"""
Скрипт для авторизации Telethon клиента.
Запустите этот скрипт один раз для создания сессии.
"""

import asyncio
import os
from utils import load_env_from_file, require_env

# Загружаем конфигурацию
load_env_from_file('config.env')

try:
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    print("✅ Telethon импортирован успешно")
except ImportError as e:
    print(f"❌ Ошибка импорта telethon: {e}")
    print("Установите telethon: pip install telethon")
    exit(1)

# Получаем API ключи
try:
    APP_ID = int(require_env("TG_APP_ID"))
    APP_HASH = require_env("TG_APP_HASH")
    print(f"✅ API ключи загружены: APP_ID={APP_ID}")
except RuntimeError as e:
    print(f"❌ {e}")
    print("Получить ключи можно на https://my.telegram.org/auth")
    exit(1)

# Определяем имя сессии
session_string = os.getenv("TG_SESSION_STRING")
session_name = os.getenv("TG_SESSION_NAME", "parser_session")

async def main():
    print("\n🚀 Запуск авторизации Telethon клиента...")

    # Создаем клиент
    if session_string and session_string.strip():
        try:
            print("🔑 Используем строковую сессию")
            client = TelegramClient(StringSession(session_string), APP_ID, APP_HASH)
        except ValueError as e:
            print(f"❌ Некорректная строковая сессия: {e}")
            print("Будет использоваться файловая сессия")
            client = TelegramClient(session_name, APP_ID, APP_HASH)
    else:
        print(f"📁 Используем файловую сессию: {session_name}.session")
        client = TelegramClient(session_name, APP_ID, APP_HASH)

    # Подключаемся
    print("🔌 Подключение к Telegram...")
    await client.connect()

    # Проверяем авторизацию
    if await client.is_user_authorized():
        print("✅ Клиент уже авторизован!")
        me = await client.get_me()
        print(f"👤 Авторизован как: {me.first_name} (@{me.username})")
    else:
        print("❌ Клиент не авторизован")
        print("📱 Отправьте код авторизации...")

        # Запрашиваем телефон
        phone = input("Введите номер телефона (+7...): ").strip()

        # Отправляем код
        await client.send_code_request(phone)
        code = input("Введите код из Telegram: ").strip()

        # Авторизуемся
        try:
            await client.sign_in(phone, code)
            print("✅ Авторизация успешна!")
        except Exception as e:
            print(f"❌ Ошибка авторизации: {e}")
            return

    # Получаем строковую сессию для сохранения
    if not session_string:
        saved_session_string = client.session.save()
        print("\n💾 Строковая сессия (скопируйте в config.env):")
        print(f"TG_SESSION_STRING={saved_session_string}")
        print("\nДобавьте эту строку в файл config.env")

    # Тестируем получение каналов
    print("\n🧪 Тестирование API...")
    try:
        # Получаем информацию о себе
        me = await client.get_me()
        print(f"✅ API работает. Пользователь: {me.first_name}")

        # Проверяем доступ к каналу
        try:
            # Попробуем получить информацию о канале @python (должен существовать)
            entity = await client.get_entity("@python")
            print(f"✅ Доступ к каналам работает. Тестовый канал: {entity.title}")
        except Exception as e:
            print(f"⚠️  Не удалось получить доступ к тестовому каналу: {e}")

    except Exception as e:
        print(f"❌ Ошибка тестирования API: {e}")

    # Закрываем соединение
    await client.disconnect()
    print("\n👋 Готово! Клиент настроен и протестирован.")

if __name__ == "__main__":
    asyncio.run(main())
