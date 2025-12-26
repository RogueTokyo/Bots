import logging
from typing import Generator, Any
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from bot.config import Config

logger = logging.getLogger(__name__)

try:
    # Создаем engine для подключения к базе данных
    logger.info("Инициализация подключения к базе данных...")
    logger.debug(f"Database URI: {Config.SQLALCHEMY_DATABASE_URI.replace('://', '://[HIDDEN]@')}")

    engine = create_engine(
        Config.SQLALCHEMY_DATABASE_URI,
        echo=False,  # Отключаем echo в продакшене
        pool_pre_ping=True,  # Проверяем соединение перед использованием
        pool_recycle=300,  # Пересоздаем соединение каждые 5 минут
        pool_size=10,  # Размер пула соединений
        max_overflow=20,  # Максимальное количество дополнительных соединений
        pool_timeout=30,  # Таймаут ожидания соединения из пула
        connect_args={
            "connect_timeout": 10,  # Таймаут подключения 10 секунд
            "application_name": "ShopManagerBot",  # Имя приложения для мониторинга
        }
    )

except SQLAlchemyError as db_error:
    logger.critical(f" Критическая ошибка при подключении к базе данных: {db_error}")
    logger.critical("Проверьте настройки подключения в config.py")
    raise
except Exception as unexpected_error:
    logger.critical(f" Неожиданная ошибка при инициализации базы данных: {unexpected_error}")
    raise

# Создаем базовый класс для моделей
Base = declarative_base()

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """
    Функция для получения сессии базы данных.
    Используется в зависимостях FastAPI или как контекстный менеджер.
    """
    db: Optional[Session] = None
    try:
        db = SessionLocal()
        logger.debug("Создана новая сессия базы данных")
        yield db
    except SQLAlchemyError as db_error:
        logger.error(f"Ошибка в сессии базы данных: {db_error}")
        raise
    except Exception as unexpected_error:
        logger.error(f"Неожиданная ошибка в сессии базы данных: {unexpected_error}")
        raise
    finally:
        if db:
            try:
                db.close()
                logger.debug("Сессия базы данных закрыта")
            except Exception as close_error:
                logger.warning(f"Ошибка при закрытии сессии базы данных: {close_error}")

def create_tables() -> None:
    """
    Создает все таблицы в базе данных на основе определенных моделей.
    """
    try:
        logger.info("Создание таблиц в базе данных...")
        Base.metadata.create_all(bind=engine)
        logger.info(" Все таблицы успешно созданы")
    except SQLAlchemyError as db_error:
        logger.error(f" Ошибка при создании таблиц: {db_error}")
        logger.error("Возможно, таблицы уже существуют или есть проблемы с правами")
        raise
    except Exception as unexpected_error:
        logger.error(f" Неожиданная ошибка при создании таблиц: {unexpected_error}")
        raise

def check_db_connection() -> bool:
    """
    Проверяет подключение к базе данных.

    Returns:
        True если подключение успешно, False в противном случае
    """
    try:
        with engine.connect() as connection:
            logger.info("Подключение к базе данных успешно установлено")
            return True
    except Exception as e:
        logger.error(f"Ошибка подключения к базе данных: {e}")
        return False
