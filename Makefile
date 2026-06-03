.PHONY: help up down dev-up dev-down dev-logs logs sync migrate test lint ci grpc-gen

BACKEND     := backend
COMPOSE     := compose
COMPOSE_DEV := -f docker-compose.dev.yml
DC_RUN_API  = cd $(COMPOSE) && docker compose $(COMPOSE_DEV) run --rm --no-deps --entrypoint ""

help:
	@echo.
	@echo   make up          — Docker prod
	@echo   make dev-up      — Docker dev + hot reload
	@echo   make down        — остановить prod
	@echo   make dev-down    — остановить dev
	@echo   make logs        — логи api (prod)
	@echo   make dev-logs    — логи api (dev)
	@echo   make sync        — пересобрать dev-образ (после pyproject.toml)
	@echo   make migrate     — alembic upgrade head (в контейнере, нужен compose/.env)
	@echo   make test        — pytest в контейнере
	@echo   make lint        — ruff в контейнере
	@echo   make ci          — lint + test в контейнере
	@echo   make grpc-gen    — regenerate grpc stubs
	@echo.

up:
	cd $(COMPOSE) && docker compose up -d --build

down:
	cd $(COMPOSE) && docker compose down

dev-up:
	cd $(COMPOSE) && docker compose $(COMPOSE_DEV) up -d --build

dev-down:
	cd $(COMPOSE) && docker compose $(COMPOSE_DEV) down

logs:
	cd $(COMPOSE) && docker compose logs -f api

dev-logs:
	cd $(COMPOSE) && docker compose $(COMPOSE_DEV) logs -f api

sync:
	cd $(COMPOSE) && docker compose $(COMPOSE_DEV) build api

migrate:
	cd $(COMPOSE) && docker compose $(COMPOSE_DEV) run --rm --entrypoint "" api alembic upgrade head

test:
	$(DC_RUN_API) api uv run pytest -q

lint:
	$(DC_RUN_API) api uv run ruff check .

ci: lint test

grpc-gen:
	cd $(BACKEND) && uv run python scripts/generate_grpc_stubs.py
