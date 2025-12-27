# Парсер Telegram каналов

Бот для поиска сообщений в Telegram каналах по ключевым словам в реальном времени с использованием API Telethon.

## Быстрый старт

```bash
cd parser
pip install -r requirements.txt
python3 auth_telethon.py
python3 run_bot.py
```

## Структура проекта

```
parser/
├── Парсер.py           # Основной модуль бота
├── utils.py            # Утилиты
├── auth_telethon.py    # Скрипт авторизации
├── test_parsing.py     # Скрипт тестирования
├── run_bot.py          # Запуск бота
├── config.env          # Конфигурация (создайте сами)
├── requirements.txt    # Зависимости
├── cache/              # Кеш результатов поиска
└── requests/           # Сохраненные запросы
```

## Настройка

1. Установите зависимости: `pip install -r requirements.txt`
2. Создайте `config.env` с API ключами
3. Авторизуйтесь в Telethon: `python3 auth_telethon.py`
4. Запустите бота: `python3 run_bot.py`

Подробная документация в `parser/README.md`.
