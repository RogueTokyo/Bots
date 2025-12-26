"""
Интерфейсы и абстрактные базовые классы для чистой архитектуры
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Protocol, Tuple
from dataclasses import dataclass


@dataclass
class ProductData:
    """Структура данных товара"""
    name: str
    quantity: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "quantity": self.quantity
        }


@dataclass
class ShopData:
    """Структура данных магазина"""
    id: Optional[int]
    user_id: int
    name: str
    client_id: str
    api_key: str
    is_active: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "client_id": self.client_id,
            "api_key": self.api_key,
            "is_active": self.is_active
        }


class IShopRepository(Protocol):
    """Интерфейс репозитория магазинов"""

    def create_shop(self, shop_data: ShopData) -> ShopData:
        """Создать новый магазин"""
        ...

    def get_shop_by_id(self, shop_id: int) -> Optional[ShopData]:
        """Получить магазин по ID"""
        ...

    def get_shops_by_user_id(self, user_id: int) -> List[ShopData]:
        """Получить все магазины пользователя"""
        ...

    def get_active_shops_by_user_id(self, user_id: int) -> List[ShopData]:
        """Получить активные магазины пользователя"""
        ...

    def update_shop(self, shop_id: int, shop_data: ShopData) -> Optional[ShopData]:
        """Обновить данные магазина"""
        ...

    def delete_shop(self, shop_id: int) -> bool:
        """Удалить магазин"""
        ...


class IAPIClient(Protocol):
    """Интерфейс API клиента"""

    async def send_products(
        self,
        client_id: str,
        api_key: str,
        products: Dict[str, int]
    ) -> 'APIResponse':
        """Отправить продукты на API"""
        ...


class IExcelProcessor(Protocol):
    """Интерфейс обработчика Excel файлов"""

    async def process_products_file(
        self,
        file_path: str,
        user_id: int
    ) -> Tuple[List[ProductData], List[str]]:
        """Обработать Excel файл с продуктами

        Returns:
            Кортеж: (список продуктов, список ошибок)
        """
        ...


@dataclass
class APIResponse:
    """Стандартизированная структура ответа API"""
    success: bool
    status_code: int
    data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    request_duration: float = 0.0
    retry_after: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "status_code": self.status_code,
            "data": self.data,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "request_duration": self.request_duration,
            "retry_after": self.retry_after
        }


class IErrorHandler(Protocol):
    """Интерфейс обработчика ошибок"""

    async def handle_error(
        self,
        error: Exception,
        context: str,
        user_message: Optional[str] = None
    ) -> str:
        """Обработать ошибку и вернуть сообщение для пользователя"""
        ...


class IMessageService(Protocol):
    """Интерфейс сервиса сообщений"""

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: Optional[Any] = None
    ) -> bool:
        """Отправить сообщение пользователю"""
        ...

    async def send_error_message(
        self,
        chat_id: int,
        error: Exception,
        context: str
    ) -> bool:
        """Отправить сообщение об ошибке"""
        ...


class IShopService(Protocol):
    """Интерфейс сервиса управления магазинами"""

    async def create_shop(
        self,
        user_id: int,
        name: str,
        client_id: str,
        api_key: str
    ) -> ShopData:
        """Создать новый магазин"""
        ...

    async def get_user_active_shops(self, user_id: int) -> List[ShopData]:
        """Получить активные магазины пользователя"""
        ...

    async def validate_shop_access(self, user_id: int, shop_id: int) -> Optional[ShopData]:
        """Проверить доступ пользователя к магазину"""
        ...
