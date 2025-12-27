#!/usr/bin/env python3
"""
Скрипт для тестирования парсинга Telegram каналов.
Запустите после настройки telethon клиента.
"""

import asyncio
import os
from utils import load_env_from_file, require_env

# Загружаем конфигурацию
load_env_from_file('config.env')

try:
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    from telethon.errors import RPCError
    print("✅ Telethon импортирован успешно")
except ImportError as e:
    print(f"❌ Ошибка импорта telethon: {e}")
    print("Установите telethon: pip install telethon")
    exit(1)

# Получаем API ключи
try:
    APP_ID = int(require_env("TG_APP_ID"))
    APP_HASH = require_env("TG_APP_HASH")
    print("✅ API ключи загружены")
except RuntimeError as e:
    print(f"❌ {e}")
    print("Получить ключи можно на https://my.telegram.org/auth")
    exit(1)

# Настройки Telethon
session_string = os.getenv("TG_SESSION_STRING")
session_name = os.getenv("TG_SESSION_NAME", "parser_session")

if session_string and session_string.strip():
    try:
        telethon_client = TelegramClient(StringSession(session_string), APP_ID, APP_HASH)
    except ValueError as e:
        print(f"❌ Некорректная строковая сессия: {e}")
        telethon_client = TelegramClient(session_name, APP_ID, APP_HASH)
else:
    telethon_client = TelegramClient(session_name, APP_ID, APP_HASH)

async def test_connection():
    """Тест подключения к Telegram API."""
    print("\n🔌 Тестирование подключения...")

    try:
        await telethon_client.connect()
        print("✅ Подключение успешно")
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

    try:
        if await telethon_client.is_user_authorized():
            me = await telethon_client.get_me()
            print(f"✅ Авторизация успешна: {me.first_name} (@{me.username})")
            return True
        else:
            print("❌ Клиент не авторизован")
            print("Запустите auth_telethon.py для авторизации")
            return False
    except Exception as e:
        print(f"❌ Ошибка проверки авторизации: {e}")
        return False

async def test_channel_access(channel_username: str):
    """Тест доступа к каналу."""
    print(f"\n📺 Тестирование доступа к каналу {channel_username}...")

    try:
        entity = await telethon_client.get_entity(channel_username)
        print(f"✅ Доступ к каналу '{entity.title}' получен")
        print(f"   Тип: {'Канал' if getattr(entity, 'broadcast', False) else 'Группа'}")
        print(f"   Подписчиков: {getattr(entity, 'participants_count', 'N/A')}")
        return True
    except RPCError as e:
        print(f"❌ Ошибка доступа к каналу: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

async def test_message_search(channel_username: str, keywords: list, limit: int = 10):
    """Тест поиска сообщений."""
    print(f"\n🔍 Тестирование поиска в {channel_username}...")
    print(f"   Ключевые слова: {', '.join(keywords)}")
    print(f"   Лимит сообщений: {limit}")

    try:
        entity = await telethon_client.get_entity(channel_username)
    except Exception as e:
        print(f"❌ Не удалось получить доступ к каналу: {e}")
        return []

    results = []
    message_count = 0

    try:
        async for message in telethon_client.iter_messages(entity, limit=limit):
            message_count += 1
            text = message.message or ""

            if not text:
                continue

            lower_text = text.lower()
            if any(keyword.lower() in lower_text for keyword in keywords):
                snippet = text.replace("\n", " ").strip()
                if len(snippet) > 100:
                    snippet = snippet[:97] + "..."

                results.append({
                    'message_id': message.id,
                    'date': message.date.strftime("%d.%m.%y %H:%M"),
                    'snippet': snippet,
                    'link': f"https://t.me/{channel_username.lstrip('@')}/{message.id}"
                })

        print(f"✅ Просмотрено {message_count} сообщений")
        print(f"✅ Найдено совпадений: {len(results)}")

        if results:
            print("\n📋 Найденные сообщения:")
            for i, result in enumerate(results[:3], 1):  # Показываем первые 3
                print(f"{i}. [{result['date']}] {result['snippet']}")
                print(f"   🔗 {result['link']}")

        return results

    except Exception as e:
        print(f"❌ Ошибка при поиске: {e}")
        return []

async def main():
    """Основная функция тестирования."""
    print("🚀 Запуск тестирования парсера Telegram каналов")
    print("=" * 50)

    # Тест 1: Подключение
    if not await test_connection():
        print("\n❌ Тест подключения провален. Проверьте авторизацию.")
        return

    # Тест 2: Доступ к каналам
    test_channels = ["@python", "@telegram"]  # Популярные публичные каналы

    for channel in test_channels:
        if await test_channel_access(channel):
            # Тест 3: Поиск сообщений
            await test_message_search(channel, ["python", "telegram"], limit=50)
            break  # Тестируем только один успешный канал
        else:
            print(f"⚠️  Пропускаем тестирование поиска для {channel}")

    # Закрываем соединение
    await telethon_client.disconnect()

    print("\n" + "=" * 50)
    print("✅ Тестирование завершено!")
    print("\n💡 Если все тесты прошли успешно, бот готов к работе.")
    print("   Запустите бота командой: python3 run_bot.py")

if __name__ == "__main__":
    asyncio.run(main())
