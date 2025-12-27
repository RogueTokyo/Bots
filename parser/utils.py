#!/usr/bin/env python3
"""
Утилиты для проекта парсера Telegram каналов.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


def load_env_from_file(filepath: str) -> bool:
    """
    Загружает переменные окружения из файла.
    
    Args:
        filepath: Путь к файлу конфигурации (относительно текущей директории)
        
    Returns:
        True если загружены переменные, False если файла нет или он пуст
    """
    config_path = Path(filepath).resolve()
    
    if not config_path.exists():
        print(f"⚠️  Файл {filepath} не найден в {config_path.parent}")
        return False

    loaded_count = 0
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
                        loaded_count += 1
    except Exception as e:
        print(f"❌ Ошибка чтения файла {filepath}: {e}")
        return False

    if loaded_count > 0:
        print(f"✅ Загружено {loaded_count} переменных из {filepath}")
    return loaded_count > 0


def require_env(name: str) -> str:
    """
    Получить обязательную переменную окружения.
    
    Args:
        name: Имя переменной окружения
        
    Returns:
        Значение переменной окружения
        
    Raises:
        RuntimeError: Если переменная не установлена
    """
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Необходимо установить переменную окружения {name}.")
    return value


def get_env_int(name: str, default: int = 0) -> int:
    """
    Получить целочисленную переменную окружения.
    
    Args:
        name: Имя переменной окружения
        default: Значение по умолчанию
        
    Returns:
        Целочисленное значение переменной
    """
    value = os.getenv(name, str(default))
    try:
        return int(value)
    except ValueError:
        logger.warning(f"Некорректное значение {name}={value}, используется {default}")
        return default


def get_env(name: str, default: str = "") -> str:
    """
    Получить переменную окружения с значением по умолчанию.
    
    Args:
        name: Имя переменной окружения
        default: Значение по умолчанию
        
    Returns:
        Значение переменной окружения или default
    """
    return os.getenv(name, default)
