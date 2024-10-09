.PHONY: init feature-start feature-finish start-release finish-release start-hotfix finish-hotfix changelog bump branches local-up local-down local-restart dev-up dev-down dev-restart test-up test-down test-restart prod-up prod-down prod-restart logs build help lint test clean update-deps

# Переменные для выбора конфигурации
LOCAL_COMPOSE_FILE := .docker/docker-compose.local.yml
DEV_COMPOSE_FILE := .docker/docker-compose.development.yml
TEST_COMPOSE_FILE := .docker/docker-compose.test.yml
PROD_COMPOSE_FILE := .docker/docker-compose.production.yml


# Переменные для git flow
GIT_FLOW = git flow
VERSION = $(shell git describe --tags --abbrev=0)

# Инициализация Git Flow
init:
	@read -p "Введите название окружения: " environment; \
	echo "Инициализация Git Flow..."; \
	$(GIT_FLOW) init -d; \
	echo "Инициализация окружения..."; \
	pyenv install 3.12.0; \
	pyenv virtualenv 3.12.0 $$environment; \
	pyenv local $$environment; \
	pip install poetry; \
	poetry config virtualenvs.prefer-active-python true; \
	echo "Установка зависимостей..."; \
	poetry install
	
# Создание новой ветки
feature-start:
	echo "2 последних изменения в репозитории:"
	git log --oneline -4
	@read -p "Введите имя ветки: " feature; \
	echo "Создание новой ветки: $$feature"; \
	git flow feature start "$$feature"

# Завершение ветки
feature-finish:
	@echo "Название текущей ветки:"
	git branch --show-current 
	@read -p "Введите имя ветки: " feature; \
	echo "Завершение ветки: $$feature"; \
	echo "Текущий статус репозитория:"; \
	git status; \
	read -p "Хотите добавить все изменения? (y/n): " add_all; \
	if [ "$$add_all" = "y" ]; then \
		git add .; \
	else \
		read -p "Введите файлы для добавления (через пробел): " files; \
		git add $$files; \
	fi; \
	echo "Создание коммита..."; \
	git branch --show-current; \
	cz commit; \
	git flow feature finish $$feature; \
	git push --all

# Начало и завершение нового релиза
release:
	@echo "Определение следующей версии..."; \
	next_version=$$(cz bump --dry-run | grep "version" | awk '{print $$3}'); \
	if [ -z "$$next_version" ]; then \
		echo "Ошибка: Не удалось определить следующую версию."; \
		exit 1; \
	fi; \
	echo "Следующая версия: $$next_version"; \
	read -p "Подтверждаете ли вы эту версию? (y/n): " confirm; \
	if [ "$$confirm" != "y" ]; then \
		read -p "Введите номер релиза вручную: " version; \
	else \
		version=$$next_version; \
	fi; \
	echo "Создание новой ветки релиза: $$version"; \
	if ! git flow release start $$version; then \
		echo "Ошибка: Не удалось создать ветку релиза."; \
		exit 1; \
	fi; \
	echo "Завершение релиза: $$version"; \
	if ! cz changelog; then \
		echo "Ошибка: Не удалось сгенерировать changelog."; \
		exit 1; \
	fi; \
	if ! cz bump --yes; then \
		echo "Ошибка: Не удалось обновить версию."; \
		exit 1; \
	fi; \
	if ! git tag -d $$version 2>/dev/null; then \
		echo "Предупреждение: Тег $$version не найден для удаления."; \
	fi; \
	if ! git flow release finish $$version; then \
		echo "Ошибка: Не удалось завершить релиз."; \
		exit 1; \
	fi; \
	if ! git push origin master; then \
		echo "Ошибка: Не удалось отправить изменения в master."; \
		exit 1; \
	fi; \
	if ! git push origin develop; then \
		echo "Ошибка: Не удалось отправить изменения в develop."; \
		exit 1; \
	fi;
	if ! git push --tag; then \
		echo "Ошибка: Не удалось отправить теги."; \
		exit 1; \
	fi;


# Начало нового хотфикса
start-hotfix:
	@read -p "Введите номер хотфикса: " version; \
	echo "Создание новой ветки хотфикса: $$version"; \
	$(GIT_FLOW) hotfix start $$version

# Завершение хотфикса
finish-hotfix:
	@read -p "Введите номер хотфикса: " version; \
	echo "Завершение хотфикса: $$version"; \
	echo "Текущий статус репозитория:"; \
	git status; \
	read -p "Хотите добавить все изменения? (y/n): " add_all; \
	if [ "$$add_all" = "y" ]; then \
		git add .; \
	else \
		read -p "Введите файлы для добавления (через пробел): " files; \
		git add $$files; \
	fi; \
	echo "Создание коммита..."; \
	git commit -m "Завершение хотфикса: $$version"; \
	$(GIT_FLOW) hotfix finish $$version

# Генерация changelog с Commitizen
changelog:
	@echo "Создание changelog..."
	cz changelog

# Увеличение версии с Commitizen
bump:
	@echo "Увеличение версии..."
	cz bump --changelog --yes

# Просмотр текущих веток
branches:
	git branch -a

# Команды для локального окружения
local-up:
	@echo "Запуск локального окружения..."
	docker compose -f $(LOCAL_COMPOSE_FILE) up -d db redis

local-api:
	@echo "Запуск API локально..."
	poetry run python api_runner.py
	
local-bot:
	@echo "Запуск бота локально..."
	poetry run python bot_runner.py

local-celery:
	@echo "Запуск Celery worker локально..."
	poetry run celery -A celery_service.celery_app worker --loglevel=info

local-down:
	@echo "Остановка локального окружения..."
	docker compose -f $(LOCAL_COMPOSE_FILE) down
	@echo "Остановка локальных процессов..."
	pkill -f "python api_runner.py"
	pkill -f "python bot_runner.py"
	pkill -f "celery -A celery_service.celery_app worker"

local-api-down:
	@echo "Остановка API..."
	pkill -f "python api_runner.py"

local-bot-down:
	@echo "Остановка бота..."
	pkill -f "python bot_runner.py"

local-celery-down:
	@echo "Остановка Celery worker..."
	pkill -f "celery -A celery_service.celery_app worker"

local-restart: local-down local-up

# Команды для dev окружения
dev-up:
	@echo "Запуск dev окружения..."
	docker compose -f $(DEV_COMPOSE_FILE) up --build

dev-down:
	@echo "Остановка dev окружения..."
	docker compose -f $(DEV_COMPOSE_FILE) down --rmi all

dev-restart: dev-down dev-up

# Команды для test окружения
test-up:
	@echo "Запуск test окружения..."
	docker compose -f $(TEST_COMPOSE_FILE) up -d

test-down:
	@echo "Остановка test окружения..."
	docker compose -f $(TEST_COMPOSE_FILE) down

test-restart: test-down test-up

# Команды для prod окружения
prod-up:
	@echo "Запуск production окружения..."
	docker compose -f $(PROD_COMPOSE_FILE) up -d

prod-down:
	@echo "Остановка production окружения..."
	docker compose -f $(PROD_COMPOSE_FILE) down

prod-restart: prod-down prod-up

# Общие команды для Docker
logs:
	@echo "Просмотр логов контейнеров..."
	docker compose -f $(COMPOSE_FILE) logs -f

build:
	@echo "Сборка образов..."
	docker compose -f $(DEV_COMPOSE_FILE) build

# Команды для разработки и тестирования
lint:
	@echo "Запуск линтера..."
	poetry run flake8 .
	poetry run mypy .

test:
	@echo "Запуск тестов..."
	poetry run pytest

clean:
	@echo "Очистка временных файлов и кэша..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name "*.db" -delete
	rm -rf .pytest_cache
	rm -rf .mypy_cache

update-deps:
	@echo "Обновление зависимостей проекта..."
	poetry update

# Команды для работы с базой данных
revision:
	@read -p "Введите сообщение для миграции: " msg; \
	echo "Генерация миграции с сообщением: $$msg"; \
	poetry run alembic revision --autogenerate -m "$$msg"

upgrade:
	@echo "Обновление миграций"
	poetry run alembic upgrade head

shake:
	@echo "Change files"
	@read -p "Enter name of file, which need to shake [local, dev]: " file; \
	if [ "$$file" = "local" ]; then \
		cp .local.env .env; \
	elif [ "$$file" = "dev" ]; then \
		cp .dev.env .env; \
	else \
		echo "Unknown name"; \
		exit 1; \
	fi

help:
	@echo "Доступные команды:"
	@echo "  make init             - Инициализация Git Flow"
	@echo "  make feature-start    - Создание новой ветки"
	@echo "  make feature-finish   - Завершение ветки ветки"
	@echo "  make release          - Начало и завершение нового релиза"
	@echo "  make finish-release   - Завершение релиза с увеличением версии и созданием changelog"
	@echo "  make start-hotfix     - Начало нового хотфикса"
	@echo "  make finish-hotfix    - Завершение хотфикса"
	@echo "  make changelog        - Генерация changelog с Commitizen"
	@echo "  make bump             - Увеличение версии с Commitizen"
	@echo "  make branches         - Просмотр текущих веток"
	@echo "  make local-up         - Запуск локального окружения"
	@echo "  make local-down       - Остановка локального окружения"
	@echo "  make local-restart    - Перезапуск локального окружения"
	@echo "  make local-api        - Запуск API локально"
	@echo "  make local-bot        - Запуск бота локально"
	@echo "  make local-celery     - Запуск Celery worker локально"
	@echo "  make local-api-down   - Остановка локального API"
	@echo "  make local-bot-down   - Остановка локального бота"
	@echo "  make local-celery-down - Остановка локального Celery worker"
	@echo "  make dev-up           - Запуск dev окружения"
	@echo "  make dev-down         - Остановка dev окружения"
	@echo "  make dev-restart      - Перезапуск dev окружения"
	@echo "  make test-up          - Запуск test окружения"
	@echo "  make test-down        - Остановка test окружения"
	@echo "  make test-restart     - Перезапуск test окружения"
	@echo "  make prod-up          - Запуск production окружения"
	@echo "  make prod-down        - Остановка production окружения"
	@echo "  make prod-restart     - Перезапуск production окружения"
	@echo "  make logs             - Просмотр логов контейнеров"
	@echo "  make build            - Сборка образов"
	@echo "  make lint             - Запуск линтера"
	@echo "  make test             - Запуск тестов"
	@echo "  make clean            - Очистка временных файлов и кэша"
	@echo "  make update-deps      - Обновление зависимостей проекта"
	@echo "  make revision         - Создание новой миграции базы данных"
	@echo "  make upgrade          - Применение миграций базы данных"
	@echo "  make shake            - Change files [.local.env, .dev.env] to .env"
	@echo "  make help             - Вывод справки по доступным командам"

# Позволяет передавать аргументы в команды
%:
	@:
