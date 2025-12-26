"""
Сервис обработки ошибок с уведомлениями пользователей
"""

import logging
import traceback
from typing import Optional, Dict, Any
from bot.utils.interfaces import IErrorHandler, APIResponse

logger = logging.getLogger(__name__)


class ErrorHandler(IErrorHandler):
    """Сервис для обработки ошибок и генерации сообщений для пользователей"""

    # Словарь соответствий типов ошибок пользовательским сообщениям
    ERROR_MESSAGES: Dict[str, str] = {
        "validation_error": "Ошибка валидации данных. Проверьте правильность введенной информации.",
        "network_error": "Сетевая ошибка. Проверьте подключение к интернету и повторите попытку.",
        "timeout_error": "Превышено время ожидания. Сервер не отвечает. Попробуйте позже.",
        "auth_error": "Ошибка авторизации. Проверьте API ключ магазина.",
        "server_error": "Ошибка сервера. Попробуйте позже или обратитесь в поддержку.",
        "unknown_error": "Неизвестная ошибка. Попробуйте позже или обратитесь в поддержку.",
    }

    def __init__(self, max_traceback_length: int = 1000):
        self.max_traceback_length = max_traceback_length

    async def handle_error(
        self,
        error: Exception,
        context: str,
        user_message: Optional[str] = None
    ) -> str:
        """
        Обработать ошибку и вернуть пользовательское сообщение

        Args:
            error: Исключение
            context: Контекст, где произошла ошибка
            user_message: Пользовательское сообщение (опционально)

        Returns:
            Сообщение для пользователя
        """
        # Логируем ошибку с полным traceback
        logger.error(f"Ошибка в контексте '{context}': {error}")
        logger.error(f"Traceback: {traceback.format_exc()}")

        # Если передано пользовательское сообщение, используем его
        if user_message:
            return user_message

        # Определяем тип ошибки и возвращаем соответствующее сообщение
        error_type = self._classify_error(error)

        if isinstance(error, APIResponse) and error.error_type:
            # Если это APIResponse с типом ошибки
            return self.ERROR_MESSAGES.get(
                error.error_type,
                self.ERROR_MESSAGES["unknown_error"]
            )

        # Для обычных исключений
        return self.ERROR_MESSAGES.get(error_type, self.ERROR_MESSAGES["unknown_error"])

    def _classify_error(self, error: Exception) -> str:
        """
        Классифицировать ошибку по типу

        Args:
            error: Исключение

        Returns:
            Тип ошибки как строка
        """
        error_name = type(error).__name__
        error_message = str(error).lower()

        # Классификация по имени исключения
        if "timeout" in error_name.lower() or "timeout" in error_message:
            return "timeout_error"
        elif "connection" in error_name.lower() or "network" in error_message:
            return "network_error"
        elif "auth" in error_name.lower() or "unauthorized" in error_message or "forbidden" in error_message:
            return "auth_error"
        elif "validation" in error_name.lower() or "value" in error_message:
            return "validation_error"
        elif "server" in error_name.lower() or "internal" in error_message:
            return "server_error"

        # Классификация по сообщению ошибки
        if "превышено время" in error_message or "timeout" in error_message:
            return "timeout_error"
        elif "подключение" in error_message or "connection" in error_message:
            return "network_error"
        elif "авторизация" in error_message or "api key" in error_message:
            return "auth_error"
        elif "валидация" in error_message or "некорректные данные" in error_message:
            return "validation_error"

        return "unknown_error"

    async def handle_api_error(self, api_response: APIResponse, context: str) -> str:
        """
        Обработать ошибку API ответа

        Args:
            api_response: Ответ API с ошибкой
            context: Контекст операции

        Returns:
            Сообщение для пользователя
        """
        logger.warning(
            f"API ошибка в контексте '{context}': "
            f"HTTP {api_response.status_code}, "
            f"тип: {api_response.error_type}, "
            f"сообщение: {api_response.error_message}"
        )

        if api_response.error_type:
            base_message = self.ERROR_MESSAGES.get(
                api_response.error_type,
                self.ERROR_MESSAGES["unknown_error"]
            )
        else:
            base_message = self.ERROR_MESSAGES["server_error"]

        # Добавляем дополнительную информацию
        if api_response.retry_after:
            base_message += f"\n\nПовторите через {api_response.retry_after} секунд."

        return base_message

    async def create_detailed_error_message(
        self,
        error: Exception,
        context: str,
        include_traceback: bool = False
    ) -> Dict[str, Any]:
        """
        Создать детальное сообщение об ошибке для отладки

        Args:
            error: Исключение
            context: Контекст ошибки
            include_traceback: Включать ли traceback

        Returns:
            Словарь с деталями ошибки
        """
        error_details = {
            "context": context,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "user_message": await self.handle_error(error, context),
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }

        if include_traceback:
            error_details["traceback"] = traceback.format_exc()

        return error_details


# Глобальный экземпляр обработчика ошибок
error_handler = ErrorHandler()
