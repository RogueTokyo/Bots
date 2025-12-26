"""
Утилиты и вспомогательные функции
"""

from .database import SessionLocal, create_tables, get_db, check_db_connection
from .states import ShopStates
from .interfaces import (
    ProductData, ShopData, IShopRepository, IAPIClient,
    IExcelProcessor, APIResponse, IErrorHandler,
    IMessageService, IShopService
)
from .cache import cache, cached, invalidate_cache

# Импортируем клавиатуры по требованию для избежания циклических импортов
def get_main_menu_keyboard():
    from .keyboards import get_main_menu_keyboard as _get_main_menu_keyboard
    return _get_main_menu_keyboard()

def get_confirmation_keyboard():
    from .keyboards import get_confirmation_keyboard as _get_confirmation_keyboard
    return _get_confirmation_keyboard()

def get_shops_keyboard(*args, **kwargs):
    from .keyboards import get_shops_keyboard as _get_shops_keyboard
    return _get_shops_keyboard(*args, **kwargs)

def get_shop_actions_keyboard(*args, **kwargs):
    from .keyboards import get_shop_actions_keyboard as _get_shop_actions_keyboard
    return _get_shop_actions_keyboard(*args, **kwargs)

def get_products_count_keyboard(*args, **kwargs):
    from .keyboards import get_products_count_keyboard as _get_products_count_keyboard
    return _get_products_count_keyboard(*args, **kwargs)

__all__ = [
    'SessionLocal', 'create_tables', 'get_db', 'check_db_connection',
    'get_main_menu_keyboard', 'get_confirmation_keyboard',
    'get_shops_keyboard', 'get_shop_actions_keyboard', 'get_products_count_keyboard',
    'ShopStates',
    'ProductData', 'ShopData', 'IShopRepository', 'IAPIClient',
    'IExcelProcessor', 'APIResponse', 'IErrorHandler',
    'IMessageService', 'IShopService',
    'cache', 'cached', 'invalidate_cache'
]
