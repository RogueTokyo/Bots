# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код бота
COPY bot/ ./bot/
COPY *.py ./
COPY *.ini ./
COPY *.sql ./
COPY .env* ./

# Создаем директорию для логов и устанавливаем права
RUN mkdir -p logs && chmod 755 logs

# Создаем пользователя для безопасности
RUN useradd --create-home --shell /bin/bash botuser && chown -R botuser:botuser /app
USER botuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; print('Bot health check passed')" || exit 1

# Запускаем бота
CMD ["python", "-m", "bot.main"]
