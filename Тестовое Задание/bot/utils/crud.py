import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import List, Optional, Union
from bot.models import Shop
from bot.utils.database import SessionLocal
from bot.utils.cache import cached, invalidate_cache

logger = logging.getLogger(__name__)

# Pydantic модели для валидации данных (опционально, но рекомендуется)
from pydantic import BaseModel

class ShopCreate(BaseModel):
    user_id: int
    name: str
    client_id: str
    api_key: str
    is_active: bool = True

class ShopUpdate(BaseModel):
    name: Optional[str] = None
    client_id: Optional[str] = None
    api_key: Optional[str] = None
    is_active: Optional[bool] = None

def create_shop(db: Session, shop_data: ShopCreate) -> Shop:
    """
    Создает новый магазин в базе данных.

    Args:
        db: Сессия базы данных
        shop_data: Данные для создания магазина

    Returns:
        Созданный объект Shop

    Raises:
        IntegrityError: Если произошла ошибка целостности данных
        SQLAlchemyError: При других ошибках базы данных
    """
    try:
        logger.debug(f"Создание магазина: user_id={shop_data.user_id}, name='{shop_data.name}', client_id='{shop_data.client_id}'")

        db_shop = Shop(
            user_id=shop_data.user_id,
            name=shop_data.name,
            client_id=shop_data.client_id,
            api_key=shop_data.api_key,
            is_active=shop_data.is_active
        )

        db.add(db_shop)
        db.commit()
        db.refresh(db_shop)

        # Инвалидируем кэш активных магазинов для этого пользователя
        invalidate_cache("active_shops")

        logger.info(f" Магазин успешно создан: ID={db_shop.id}, name='{db_shop.name}'")
        return db_shop

    except IntegrityError as integrity_error:
        db.rollback()
        logger.warning(f" Нарушение целостности данных при создании магазина: {integrity_error}")
        raise
    except SQLAlchemyError as db_error:
        db.rollback()
        logger.error(f" Ошибка базы данных при создании магазина: {db_error}")
        raise
    except Exception as unexpected_error:
        db.rollback()
        logger.error(f" Неожиданная ошибка при создании магазина: {unexpected_error}")
        raise

def get_shop_by_id(db: Session, shop_id: int) -> Optional[Shop]:
    """
    Получает магазин по его ID.

    Args:
        db: Сессия базы данных
        shop_id: ID магазина

    Returns:
        Объект Shop или None, если не найден
    """
    try:
        if shop_id <= 0:
            logger.warning(f"Некорректный ID магазина: {shop_id}")
            return None

        shop = db.query(Shop).filter(Shop.id == shop_id).first()

        if shop:
            logger.debug(f"Найден магазин: ID={shop.id}, name='{shop.name}'")
        else:
            logger.debug(f"Магазин с ID={shop_id} не найден")

        return shop

    except SQLAlchemyError as db_error:
        logger.error(f"Ошибка базы данных при получении магазина ID={shop_id}: {db_error}")
        raise
    except Exception as unexpected_error:
        logger.error(f"Неожиданная ошибка при получении магазина ID={shop_id}: {unexpected_error}")
        raise

def get_shops_by_user_id(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Shop]:
    """
    Получает все магазины пользователя с пагинацией.

    Args:
        db: Сессия базы данных
        user_id: ID пользователя
        skip: Количество записей для пропуска
        limit: Максимальное количество записей

    Returns:
        Список объектов Shop
    """
    return db.query(Shop).filter(Shop.user_id == user_id).offset(skip).limit(limit).all()

def get_all_shops(db: Session, skip: int = 0, limit: int = 100) -> List[Shop]:
    """
    Получает все магазины с пагинацией.

    Args:
        db: Сессия базы данных
        skip: Количество записей для пропуска
        limit: Максимальное количество записей

    Returns:
        Список объектов Shop
    """
    return db.query(Shop).offset(skip).limit(limit).all()

def update_shop(db: Session, shop_id: int, shop_update: ShopUpdate) -> Optional[Shop]:
    """
    Обновляет данные магазина.

    Args:
        db: Сессия базы данных
        shop_id: ID магазина для обновления
        shop_update: Данные для обновления

    Returns:
        Обновленный объект Shop или None, если магазин не найден

    Raises:
        IntegrityError: Если произошла ошибка целостности данных
        SQLAlchemyError: При других ошибках базы данных
    """
    try:
        if shop_id <= 0:
            logger.warning(f"Некорректный ID магазина для обновления: {shop_id}")
            return None

        db_shop = db.query(Shop).filter(Shop.id == shop_id).first()
        if not db_shop:
            logger.warning(f"Магазин с ID={shop_id} не найден для обновления")
            return None

        update_data = shop_update.dict(exclude_unset=True)

        if not update_data:
            logger.warning(f"Нет данных для обновления магазина ID={shop_id}")
            return db_shop

        logger.debug(f"Обновление магазина ID={shop_id}: {update_data}")

        # Сохраняем старые значения для логирования
        old_values = {field: getattr(db_shop, field) for field in update_data.keys()}

        for field, value in update_data.items():
            setattr(db_shop, field, value)

        db.commit()
        db.refresh(db_shop)

        # Инвалидируем кэш активных магазинов для этого пользователя
        invalidate_cache("active_shops")

        logger.info(f" Магазин ID={shop_id} успешно обновлен: {old_values} -> {update_data}")
        return db_shop

    except IntegrityError as integrity_error:
        db.rollback()
        logger.warning(f" Нарушение целостности при обновлении магазина ID={shop_id}: {integrity_error}")
        raise
    except SQLAlchemyError as db_error:
        db.rollback()
        logger.error(f" Ошибка базы данных при обновлении магазина ID={shop_id}: {db_error}")
        raise
    except Exception as unexpected_error:
        db.rollback()
        logger.error(f" Неожиданная ошибка при обновлении магазина ID={shop_id}: {unexpected_error}")
        raise

def delete_shop(db: Session, shop_id: int) -> bool:
    """
    Удаляет магазин из базы данных.

    Args:
        db: Сессия базы данных
        shop_id: ID магазина для удаления

    Returns:
        True, если магазин был удален, False, если не найден
    """
    try:
        if shop_id <= 0:
            logger.warning(f"Некорректный ID магазина для удаления: {shop_id}")
            return False

        db_shop = db.query(Shop).filter(Shop.id == shop_id).first()
        if not db_shop:
            logger.warning(f"Магазин с ID={shop_id} не найден для удаления")
            return False

        shop_name = db_shop.name
        db.delete(db_shop)
        db.commit()

        # Инвалидируем кэш активных магазинов для этого пользователя
        invalidate_cache("active_shops")

        logger.info(f" Магазин успешно удален: ID={shop_id}, name='{shop_name}'")
        return True

    except SQLAlchemyError as db_error:
        db.rollback()
        logger.error(f" Ошибка базы данных при удалении магазина ID={shop_id}: {db_error}")
        raise
    except Exception as unexpected_error:
        db.rollback()
        logger.error(f" Неожиданная ошибка при удалении магазина ID={shop_id}: {unexpected_error}")
        raise

@cached(ttl=300, key_prefix="active_shops")  # Кэшируем на 5 минут
def get_active_shops_by_user_id(db: Session, user_id: int) -> List[Shop]:
    """
    Получает только активные магазины пользователя.

    Args:
        db: Сессия базы данных
        user_id: ID пользователя

    Returns:
        Список активных объектов Shop
    """
    logger.debug(f"Получение активных магазинов для пользователя {user_id} (с кэшированием)")

    shops = db.query(Shop).filter(
        Shop.user_id == user_id,
        Shop.is_active == True
    ).all()

    logger.debug(f"Найдено {len(shops)} активных магазинов для пользователя {user_id}")
    return shops

# Вспомогательные функции для работы с сессией
def get_db_session():
    """
    Получает сессию базы данных.
    Используется как контекстный менеджер или в зависимостях.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
