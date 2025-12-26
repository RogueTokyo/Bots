"""
Сервисы приложения
"""

from .api_client import get_api_client, create_sample_products
from .error_handler import error_handler

# Для обратной совместимости
api_client = get_api_client()

__all__ = ['api_client', 'get_api_client', 'create_sample_products', 'error_handler']
