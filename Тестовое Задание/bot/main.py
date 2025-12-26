import asyncio
import logging
import sys
import traceback
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError

from bot.config import Config
from bot.utils.database import create_tables
from bot.handlers import register_handlers

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Отключаем логи от сторонних библиотек
logging.getLogger('aiogram').setLevel(logging.WARNING)
logging.getLogger('aiohttp').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)

async def error_handler(event, exception):
    """
    Глобальный обработчик ошибок для бота.

    Args:
        event: Событие, вызвавшее ошибку
        exception: Исключение
    """
    logger.error(f"Необработанная ошибка в событии {event}: {exception}")
    logger.error(f"Traceback: {traceback.format_exc()}")

    # Здесь можно добавить отправку уведомлений администратору
    # или другие действия по обработке критических ошибок

async def main():
    """Главная функция запуска бота"""

    # Проверяем наличие токена
    if not Config.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
        return

    # Создаем таблицы в базе данных
    logger.info("Создание таблиц в базе данных...")
    create_tables()

    # Инициализация бота и диспетчера
    bot = Bot(
        token=Config.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Используем MemoryStorage для FSM (для продакшена лучше Redis)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрируем все обработчики
    register_handlers(dp)

    # Регистрируем глобальный обработчик ошибок
    dp.errors.register(error_handler)

    # Запуск бота
    logger.info("Бот запущен и готов к работе!")
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except TelegramNetworkError as e:
        logger.critical(f"Критическая сетевая ошибка Telegram: {e}")
        logger.info("Рекомендуется проверить подключение к интернету")
    except TelegramBadRequest as e:
        logger.critical(f"Ошибка в запросе к Telegram API: {e}")
        logger.info("Рекомендуется проверить токен бота")
    except Exception as e:
        logger.critical(f"Критическая ошибка при работе бота: {e}")
        logger.critical(f"Traceback: {traceback.format_exc()}")
    finally:
        logger.info("Закрываем соединения...")
        try:
            await bot.session.close()
            logger.info("Соединение с Telegram API закрыто")
        except Exception as e:
            logger.error(f"Ошибка при закрытии соединения: {e}")

if __name__ == "__main__":
    asyncio.run(main())
