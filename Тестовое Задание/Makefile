# Makefile для управления в Docker

.PHONY: help build up down logs logs-bot clean health

# По умолчанию показываем помощь
help: ## Показать эту справку
	@echo "Shop Manager Bot - основные команды"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

# Определение команды docker compose
DOCKER_COMPOSE := $(shell which docker-compose > /dev/null 2>&1 && echo "docker-compose" || echo "docker compose")

# Проверка Docker
check-docker:
	@which docker > /dev/null 2>&1 || (echo "Ошибка: Docker не установлен" && exit 1)

# Проверка .env файла
check-env:
	@if [ ! -f .env ]; then \
		if [ -f token.env ]; then \
			echo "Создание .env из token.env..."; \
			cp token.env .env; \
		else \
			echo "Ошибка: .env не найден"; \
			exit 1; \
		fi; \
	fi

# Основные команды
build: check-docker check-env ## Собрать Docker образы
	$(DOCKER_COMPOSE) build --no-cache

up: check-docker check-env ## Запустить все сервисы
	$(DOCKER_COMPOSE) up -d

down: check-docker ## Остановить все сервисы
	$(DOCKER_COMPOSE) down

logs: check-docker ## Показать логи всех сервисов
	$(DOCKER_COMPOSE) logs -f

logs-bot: check-docker ## Показать логи бота
	$(DOCKER_COMPOSE) logs -f bot

clean: check-docker ## Остановить и удалить volumes
	$(DOCKER_COMPOSE) down -v

health: check-docker ## Проверить здоровье сервисов
	@echo "Проверка PostgreSQL..."
	@$(DOCKER_COMPOSE) exec postgres pg_isready -U bot_user -d bot_db || echo "PostgreSQL недоступен"
	@echo "Проверка бота..."
	@$(DOCKER_COMPOSE) exec bot python -c "print('Bot running')" || echo "Bot не запущен"
