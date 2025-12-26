## Требования

- Python 3.14+
- PostgreSQL
- Docker и Docker Compose (для развертывания)
- Токен Telegram бота

## Установка Docker

Установите Docker Desktop:

1. Скачайте Docker Desktop: https://www.docker.com/products/docker-desktop
2. Установите приложение
3. Запустите Docker Desktop
4. Проверьте установку: `docker --version`

## Быстрый старт

### 1. Установка зависимостей

```bash
pip3 install -r requirements.txt
```

**Важно:** Проект использует Python 3.14+. Все зависимости совместимы с этой версией.

### 2. Настройка переменных окружения

Файл `.env` будет создан автоматически из `.env` при первом запуске команд Docker через Makefile.

Если нужно создать `.env` вручную:

```bash
cp token.env .env
```

Обязательные переменные в `.env`:
```bash
TELEGRAM_BOT_TOKEN=your_token_here
DATABASE_URL=postgresql://bot_user:bot_password@postgres:5432/bot_db
API_BASE_URL=https://example.com
API_TIMEOUT=30
LOG_LEVEL=INFO
```

### 3. Запуск с Docker

```bash
# Запуск всех сервисов
make up

# Или вручную через docker compose
docker compose up --build -d
```

Команда `make up` автоматически проверяет Docker и создает `.env` файл из `token.env`, если его нет.

### 4. Проверка работы

```bash
# Проверка здоровья сервисов
make health

# Просмотр логов всех сервисов
make logs

# Просмотр логов бота
make logs-bot
```

## Команды Makefile

```bash
make build      # Собрать Docker образы
make up         # Запустить все сервисы
make down       # Остановить все сервисы
make logs       # Показать логи всех сервисов
make logs-bot   # Показать логи бота
make clean      # Остановить и удалить volumes
make health     # Проверить здоровье сервисов
```

## Структура проекта

```
├── docker-compose.yml          # Конфигурация Docker Compose (продакшен)
├── docker-compose.override.yml # Конфигурация для разработки
├── Dockerfile                  # Образ для бота
├── requirements.txt            # Python зависимости
├── main.py                     # Точка входа
├── Makefile                    # Команды сборки и управления
├── .gitignore                  # Игнорируемые файлы
├── mypy.ini                    # Настройки проверки типов
├── init.sql                    # Инициализация БД
├── bot/                        # Основной пакет
│   ├── main.py                # Основная логика бота
│   ├── config.py               # Конфигурация
│   ├── handlers/               # Обработчики команд
│   │   ├── __init__.py
│   │   └── handlers.py
│   ├── models/                 # Модели базы данных
│   │   ├── __init__.py
│   │   └── models.py
│   ├── services/               # Бизнес-логика и API клиент
│   │   ├── __init__.py
│   │   ├── api_client.py      # Клиент для работы с API
│   │   └── error_handler.py   # Обработка ошибок
│   └── utils/                  # Утилиты
│       ├── __init__.py
│       ├── crud.py             # CRUD операции
│       ├── database.py         # Настройки БД
│       ├── keyboards.py      # Клавиатуры Telegram
│       ├── states.py           # Состояния FSM
│       ├── interfaces.py       # Интерфейсы и протоколы
│       └── cache.py            # Кеширование
└── logs/                       # Логи приложения
```

## Зависимости

Проект использует следующие основные зависимости:

- aiogram>=3.4.0 - фреймворк для Telegram ботов
- psycopg2-binary>=2.9.10 - драйвер PostgreSQL
- SQLAlchemy>=2.0.25 - ORM для работы с БД
- pydantic>=2.12.0 - валидация данных
- pandas>=2.2.0 - обработка Excel файлов
- openpyxl==3.1.2 - работа с форматом Excel
- aiohttp==3.9.1 - асинхронные HTTP запросы

Все зависимости совместимы с Python 3.14+.

## Поддержка

При возникновении проблем:

1. Проверьте, что токен бота указан в файле `.env`
2. Убедитесь, что PostgreSQL доступна
3. Проверьте переменные окружения в файле `.env`
4. Посмотрите логи бота: `make logs-bot`
5. Проверьте здоровье сервисов: `make health`

