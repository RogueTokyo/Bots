"""
Кэширование для оптимизации производительности
"""

import asyncio
import functools
import hashlib
import json
import logging
from typing import Any, Dict, Optional, Callable, TypeVar, Union
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

T = TypeVar('T')


class SimpleCache:
    """Простой in-memory кэш с TTL"""

    def __init__(self, default_ttl: int = 300):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl

    def _generate_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Генерировать ключ кэша на основе имени функции и аргументов"""
        # Создаем сериализуемый словарь аргументов
        cache_dict = {
            'func': func_name,
            'args': args,
            'kwargs': {k: v for k, v in kwargs.items() if k != 'db'}  # Исключаем сессию БД
        }

        # Создаем хэш
        cache_str = json.dumps(cache_dict, sort_keys=True, default=str)
        return hashlib.md5(cache_str.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Получить значение из кэша"""
        if key in self._cache:
            entry = self._cache[key]
            if datetime.now() < entry['expires']:
                logger.debug(f"Cache hit for key: {key}")
                return entry['value']

            # Удаляем просроченный кэш
            del self._cache[key]
            logger.debug(f"Cache expired for key: {key}")

        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Сохранить значение в кэш"""
        expires = datetime.now() + timedelta(seconds=ttl or self.default_ttl)
        self._cache[key] = {
            'value': value,
            'expires': expires
        }
        logger.debug(f"Cached value for key: {key}, expires: {expires}")

    def invalidate(self, pattern: str = "*") -> int:
        """Очистить кэш по шаблону"""
        if pattern == "*":
            count = len(self._cache)
            self._cache.clear()
            logger.debug(f"Cleared all cache entries: {count}")
            return count

        # Для простоты очищаем весь кэш (можно улучшить для паттернов)
        count = len(self._cache)
        self._cache.clear()
        logger.debug(f"Cleared cache by pattern '{pattern}': {count} entries")
        return count


# Глобальный экземпляр кэша
cache = SimpleCache(default_ttl=300)  # 5 минут TTL по умолчанию


def cached(ttl: Optional[int] = None, key_prefix: str = ""):
    """
    Декоратор для кэширования результатов функций

    Args:
        ttl: Время жизни кэша в секундах (None = использовать значение по умолчанию)
        key_prefix: Префикс для ключей кэша
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            # Генерируем ключ кэша
            cache_key = f"{key_prefix}:{cache._generate_key(func.__name__, args, kwargs)}"

            # Проверяем кэш
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Выполняем функцию
            result = await func(*args, **kwargs)

            # Кэшируем результат
            cache.set(cache_key, result, ttl)

            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            # Генерируем ключ кэша
            cache_key = f"{key_prefix}:{cache._generate_key(func.__name__, args, kwargs)}"

            # Проверяем кэш
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Выполняем функцию
            result = func(*args, **kwargs)

            # Кэшируем результат
            cache.set(cache_key, result, ttl)

            return result

        # Выбираем wrapper в зависимости от того, асинхронная ли функция
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def invalidate_cache(pattern: str = "*") -> int:
    """
    Очистить кэш по шаблону

    Args:
        pattern: Шаблон для очистки кэша

    Returns:
        Количество очищенных записей
    """
    return cache.invalidate(pattern)
