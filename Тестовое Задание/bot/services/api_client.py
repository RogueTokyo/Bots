import asyncio
import aiohttp
import json
import logging
import traceback
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from bot.config import Config

logger = logging.getLogger(__name__)

class APIErrorType(Enum):
    """Типы ошибок API"""
    VALIDATION_ERROR = "validation_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    AUTH_ERROR = "auth_error"
    SERVER_ERROR = "server_error"
    UNKNOWN_ERROR = "unknown_error"

@dataclass
class APIResponse:
    """Структура ответа API"""
    success: bool
    status_code: int
    data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_type: Optional[APIErrorType] = None
    request_duration: float = 0.0
    retry_after: Optional[int] = None

class ShopAPIClient:
    """Клиент для работы с API магазинов"""

    def __init__(
        self,
        base_url: str = "https://api.shop.com",
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> None:
        """
        Инициализация API клиента

        Args:
            base_url: Базовый URL API
            timeout: Таймаут запросов в секундах
            max_retries: Максимальное количество повторных попыток
            retry_delay: Задержка между повторными попытками в секундах
        """
        self.base_url: str = base_url.rstrip('/')
        self.timeout: aiohttp.ClientTimeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries: int = max_retries
        self.retry_delay: float = retry_delay
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> 'ShopAPIClient':
        """Асинхронный контекстный менеджер - вход"""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Асинхронный контекстный менеджер - выход"""
        await self.close()

    async def _ensure_session(self) -> None:
        """Гарантирует, что сессия aiohttp создана"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers={
                    'User-Agent': 'ShopManagerBot/1.0',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            )

    async def close(self) -> None:
        """Закрывает сессию aiohttp"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def send_products(
        self,
        client_id: str,
        api_key: str,
        products: Dict[str, int]
    ) -> APIResponse:
        """
        Отправка списка продуктов на API магазина

        Args:
            client_id: ID клиента магазина
            api_key: API ключ магазина
            products: Словарь продуктов для отправки

        Returns:
            APIResponse с результатом отправки
        """
        # Валидация входных данных
        validation_error = self._validate_input_data(client_id, api_key, products)
        if validation_error:
            return validation_error

        start_time = asyncio.get_event_loop().time()

        try:
            # Повторные попытки при сетевых ошибках
            for attempt in range(self.max_retries + 1):
                try:
                    response = await self._send_request(client_id, api_key, products)
                    response.request_duration = asyncio.get_event_loop().time() - start_time
                    return response

                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    if attempt == self.max_retries:
                        # Последняя попытка провалилась
                        logger.error(f"Все {self.max_retries + 1} попыток отправки провалились: {e}")
                        return APIResponse(
                            success=False,
                            status_code=0,
                            error_message=f"Сетевая ошибка после {self.max_retries + 1} попыток: {str(e)}",
                            error_type=APIErrorType.NETWORK_ERROR,
                            request_duration=asyncio.get_event_loop().time() - start_time
                        )

                    # Ждем перед следующей попыткой
                    logger.warning(f"Попытка {attempt + 1} провалилась, повтор через {self.retry_delay}s: {e}")
                    await asyncio.sleep(self.retry_delay * (attempt + 1))  # Экспоненциальная задержка

        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке продуктов: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return APIResponse(
                success=False,
                status_code=0,
                error_message=f"Неожиданная ошибка: {str(e)}",
                error_type=APIErrorType.UNKNOWN_ERROR,
                request_duration=asyncio.get_event_loop().time() - start_time
            )

    async def _send_request(
        self,
        client_id: str,
        api_key: str,
        products: Dict[str, int]
    ) -> APIResponse:
        """
        Выполнение одного HTTP запроса к API

        Args:
            client_id: ID клиента магазина
            api_key: API ключ магазина
            products: Словарь продуктов

        Returns:
            APIResponse с результатом запроса
        """
        await self._ensure_session()

        url = f"{self.base_url}/products"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        payload = {
            "ClientId": client_id,
            "products": products
        }

        logger.info(f"Отправка {len(products)} продуктов для client_id: {client_id}")
        logger.debug(f"URL: {url}")
        logger.debug(f"Payload size: {len(json.dumps(payload))} bytes")

        try:
            async with self._session.post(url, headers=headers, json=payload) as response:
                response_time = asyncio.get_event_loop().time()

                logger.info(f"Ответ API для client_id {client_id}: HTTP {response.status}")

                # Читаем тело ответа с обработкой исключений
                try:
                    response_text = await response.text()
                except Exception as e:
                    logger.error(f"Ошибка чтения ответа: {e}")
                    return APIResponse(
                        success=False,
                        status_code=response.status,
                        error_message="Не удалось прочитать ответ сервера",
                        error_type=APIErrorType.SERVER_ERROR
                    )

                logger.debug(f"Response body: {response_text[:500]}..." if len(response_text) > 500 else f"Response body: {response_text}")

                # Определяем тип ошибки по HTTP статусу
                if response.status == 200:
                    return await self._handle_success_response(response, response_text, client_id, len(products))
                elif response.status == 401 or response.status == 403:
                    return self._handle_auth_error(response, response_text)
                elif response.status == 422 or response.status == 400:
                    return self._handle_validation_error(response, response_text)
                elif response.status >= 500:
                    return self._handle_server_error(response, response_text)
                elif response.status == 429:
                    return self._handle_rate_limit_error(response, response_text)
                else:
                    return self._handle_generic_error(response, response_text)

        except asyncio.TimeoutError:
            logger.error(f"Таймаут запроса для client_id {client_id}")
            return APIResponse(
                success=False,
                status_code=0,
                error_message="Превышено время ожидания ответа сервера",
                error_type=APIErrorType.TIMEOUT_ERROR
            )

        except aiohttp.ClientConnectorError as e:
            logger.error(f"Ошибка подключения для client_id {client_id}: {e}")
            return APIResponse(
                success=False,
                status_code=0,
                error_message=f"Не удалось подключиться к серверу: {str(e)}",
                error_type=APIErrorType.NETWORK_ERROR
            )

        except aiohttp.ClientError as e:
            logger.error(f"Сетевая ошибка для client_id {client_id}: {e}")
            return APIResponse(
                success=False,
                status_code=0,
                error_message=f"Сетевая ошибка: {str(e)}",
                error_type=APIErrorType.NETWORK_ERROR
            )

    async def _handle_success_response(
        self,
        response: aiohttp.ClientResponse,
        response_text: str,
        client_id: str,
        products_count: int
    ) -> APIResponse:
        """Обработка успешного ответа (200 OK)"""
        try:
            data = json.loads(response_text)
            logger.info(f"Успешная отправка для client_id: {client_id} ({products_count} продуктов)")
            return APIResponse(
                success=True,
                status_code=response.status,
                data=data
            )
        except json.JSONDecodeError as json_error:
            logger.warning(f"Некорректный JSON ответ для client_id {client_id}: {json_error}")
            logger.warning(f"Response text: {response_text}")
            return APIResponse(
                success=False,
                status_code=response.status,
                error_message="Сервер вернул некорректный JSON ответ",
                error_type=APIErrorType.SERVER_ERROR,
                data={"raw_response": response_text}
            )

    def _handle_auth_error(self, response: aiohttp.ClientResponse, response_text: str) -> APIResponse:
        """Обработка ошибок авторизации (401, 403)"""
        error_msg = "Ошибка авторизации. Проверьте API ключ магазина."
        try:
            error_data = json.loads(response_text)
            if "message" in error_data:
                error_msg = f"Ошибка авторизации: {error_data['message']}"
        except:
            pass

        return APIResponse(
            success=False,
            status_code=response.status,
            error_message=error_msg,
            error_type=APIErrorType.AUTH_ERROR,
            data={"raw_response": response_text}
        )

    def _handle_validation_error(self, response: aiohttp.ClientResponse, response_text: str) -> APIResponse:
        """Обработка ошибок валидации (400, 422)"""
        error_msg = "Ошибка валидации данных. Проверьте формат отправляемых данных."
        try:
            error_data = json.loads(response_text)
            if "message" in error_data:
                error_msg = f"Ошибка валидации: {error_data['message']}"
            elif "errors" in error_data:
                errors = error_data["errors"]
                if isinstance(errors, list):
                    error_msg = f"Ошибки валидации: {'; '.join(errors)}"
                elif isinstance(errors, dict):
                    error_list = [f"{k}: {v}" for k, v in errors.items()]
                    error_msg = f"Ошибки валидации: {'; '.join(error_list)}"
        except:
            pass

        return APIResponse(
            success=False,
            status_code=response.status,
            error_message=error_msg,
            error_type=APIErrorType.VALIDATION_ERROR,
            data={"raw_response": response_text}
        )

    def _handle_server_error(self, response: aiohttp.ClientResponse, response_text: str) -> APIResponse:
        """Обработка серверных ошибок (5xx)"""
        error_msg = "Внутренняя ошибка сервера. Попробуйте позже."
        try:
            error_data = json.loads(response_text)
            if "message" in error_data:
                error_msg = f"Ошибка сервера: {error_data['message']}"
        except:
            pass

        return APIResponse(
            success=False,
            status_code=response.status,
            error_message=error_msg,
            error_type=APIErrorType.SERVER_ERROR,
            data={"raw_response": response_text}
        )

    def _handle_rate_limit_error(self, response: aiohttp.ClientResponse, response_text: str) -> APIResponse:
        """Обработка ошибки ограничения скорости (429)"""
        retry_after = response.headers.get('Retry-After')
        retry_seconds = int(retry_after) if retry_after and retry_after.isdigit() else None

        error_msg = f"Превышен лимит запросов. "
        if retry_seconds:
            error_msg += f"Повторите через {retry_seconds} секунд."
        else:
            error_msg += "Попробуйте позже."

        return APIResponse(
            success=False,
            status_code=response.status,
            error_message=error_msg,
            error_type=APIErrorType.SERVER_ERROR,
            retry_after=retry_seconds,
            data={"raw_response": response_text}
        )

    def _handle_generic_error(self, response: aiohttp.ClientResponse, response_text: str) -> APIResponse:
        """Обработка остальных HTTP ошибок"""
        error_msg = f"HTTP ошибка {response.status}"
        try:
            error_data = json.loads(response_text)
            if "message" in error_data:
                error_msg = error_data["message"]
        except:
            pass

        return APIResponse(
            success=False,
            status_code=response.status,
            error_message=error_msg,
            error_type=APIErrorType.UNKNOWN_ERROR,
            data={"raw_response": response_text}
        )

    def _validate_input_data(
        self,
        client_id: str,
        api_key: str,
        products: Dict[str, int]
    ) -> Optional[APIResponse]:
        """
        Валидация входных данных

        Returns:
            APIResponse с ошибкой или None если данные корректны
        """
        if not isinstance(client_id, str) or not client_id.strip():
            return APIResponse(
                success=False,
                status_code=0,
                error_message="Client ID должен быть непустой строкой",
                error_type=APIErrorType.VALIDATION_ERROR
            )

        if not isinstance(api_key, str) or not api_key.strip():
            return APIResponse(
                success=False,
                status_code=0,
                error_message="API Key должен быть непустой строкой",
                error_type=APIErrorType.VALIDATION_ERROR
            )

        if not isinstance(products, dict) or len(products) == 0:
            return APIResponse(
                success=False,
                status_code=0,
                error_message="Список продуктов должен быть непустым словарём",
                error_type=APIErrorType.VALIDATION_ERROR
            )

        # Проверка корректности значений продуктов
        for product_name, quantity in products.items():
            if not isinstance(product_name, str) or not product_name.strip():
                return APIResponse(
                    success=False,
                    status_code=0,
                    error_message=f"Название продукта не может быть пустым: '{product_name}'",
                    error_type=APIErrorType.VALIDATION_ERROR
                )
            if not isinstance(quantity, int) or quantity < 0:
                return APIResponse(
                    success=False,
                    status_code=0,
                    error_message=f"Количество должно быть неотрицательным целым числом: {quantity}",
                    error_type=APIErrorType.VALIDATION_ERROR
                )

        return None
    async def test_connection(self, client_id: str, api_key: str) -> APIResponse:
        """
        Тестовое подключение к API

        Args:
            client_id: ID клиента магазина
            api_key: API ключ магазина

        Returns:
            APIResponse с результатом теста
        """
        # Валидация входных данных
        if not client_id or not client_id.strip():
            return APIResponse(
                success=False,
                status_code=0,
                error_message="Client ID не может быть пустым"
            )

        if not api_key or not api_key.strip():
            return APIResponse(
                success=False,
                status_code=0,
                error_message="API Key не может быть пустым"
            )

        # Пробуем несколько возможных endpoint'ов для проверки здоровья
        health_endpoints = [
            "/health",
            "/status",
            "/ping",
            "/api/health",
            "/api/v1/health"
        ]

        last_error = None

        for endpoint in health_endpoints:
            url = f"{self.base_url.rstrip('/')}{endpoint}"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "ShopManagerBot/1.0"
            }

            payload = {"client_id": client_id}

            logger.debug(f"Проверка endpoint: {url}")

            try:
                timeout = aiohttp.ClientTimeout(total=10)  # 10 секунд на проверку
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    start_time = asyncio.get_event_loop().time()

                    async with session.get(url, headers=headers, json=payload) as response:
                        end_time = asyncio.get_event_loop().time()
                        response_time = end_time - start_time

                        logger.info(f"Тестовое подключение для client_id {client_id}: HTTP {response.status} ({response_time:.2f}s)")

                        if response.status in [200, 201, 202]:
                            logger.info(f" Успешное подключение к API для client_id {client_id}")
                            return APIResponse(
                                success=True,
                                status_code=response.status,
                                data={
                                    "message": "Соединение успешно",
                                    "endpoint": endpoint,
                                    "response_time": round(response_time, 2)
                                }
                            )
                        elif response.status == 401:
                            logger.warning(f" Ошибка аутентификации при тесте для client_id {client_id}")
                            return APIResponse(
                                success=False,
                                status_code=response.status,
                                error_message="Ошибка аутентификации. Проверьте API ключ."
                            )
                        elif response.status == 403:
                            logger.warning(f" Нет доступа при тесте для client_id {client_id}")
                            return APIResponse(
                                success=False,
                                status_code=response.status,
                                error_message="Нет прав доступа к API."
                            )
                        elif response.status == 404:
                            # 404 может означать, что endpoint не существует, продолжаем проверку
                            logger.debug(f"Endpoint {endpoint} не найден (404), пробуем следующий")
                            last_error = f"Endpoint {endpoint} не найден"
                            continue
                        else:
                            # Другие ошибки
                            logger.warning(f"Ошибка при тесте endpoint {endpoint}: HTTP {response.status}")
                            last_error = f"HTTP {response.status} на endpoint {endpoint}"
                            continue

            except asyncio.TimeoutError:
                logger.warning(f" Таймаут при проверке endpoint {endpoint} для client_id {client_id}")
                last_error = f"Таймаут при подключении к {endpoint}"
                continue

            except aiohttp.ClientConnectorError as connector_error:
                logger.warning(f" Ошибка соединения при проверке endpoint {endpoint}: {connector_error}")
                last_error = f"Не удалось подключиться к {endpoint}"
                continue

            except aiohttp.ClientSSLError as ssl_error:
                logger.warning(f" SSL ошибка при проверке endpoint {endpoint}: {ssl_error}")
                last_error = f"SSL ошибка при подключении к {endpoint}"
                return APIResponse(
                    success=False,
                    status_code=0,
                    error_message="Ошибка SSL сертификата. Проверьте настройки безопасности."
                )

            except Exception as endpoint_error:
                logger.warning(f"Ошибка при проверке endpoint {endpoint}: {endpoint_error}")
                last_error = f"Ошибка при подключении к {endpoint}: {str(endpoint_error)}"
                continue

        # Если ни один endpoint не сработал
        logger.error(f" Все endpoints недоступны для client_id {client_id}")
        return APIResponse(
            success=False,
            status_code=0,
            error_message=f"Не удалось подключиться к API. Последняя ошибка: {last_error or 'Неизвестная ошибка'}"
        )

def create_sample_products(count: int = 3) -> List[Dict[str, Any]]:
    """
    Создает пример списка продуктов для тестирования

    Args:
        count: Количество продуктов для создания

    Returns:
        Список продуктов
    """
    products = []
    for i in range(1, count + 1):
        product = {
            "id": f"prod_{i:03d}",
            "name": f"Продукт {i}",
            "sku": f"SKU{i:03d}",
            "price": 100.0 + (i * 10),
            "quantity": i * 5,
            "category": "Категория товаров",
            "description": f"Описание продукта {i}",
            "active": True
        }
        products.append(product)

    return products

# Глобальный экземпляр API клиента
# Создание отложено до момента первого использования
_api_client_instance: Optional[ShopAPIClient] = None

def get_api_client() -> ShopAPIClient:
    """Получить глобальный экземпляр API клиента"""
    global _api_client_instance
    if _api_client_instance is None:
        _api_client_instance = ShopAPIClient(
            base_url=Config.API_BASE_URL,
            timeout=Config.API_TIMEOUT
        )
    return _api_client_instance

# Для обратной совместимости
api_client = None  # Будет инициализирован при первом использовании
