.PHONY: help init install run test test-integration docker-up docker-down docker-clean format lint clean

# Help command to list targets
help:
	@echo "Studycast Backend Makefile"
	@echo "--------------------------"
	@echo "init             - Initialize environment files (.env, .env.docker)"
	@echo "install          - Install dependencies using uv and setup pre-commit"
	@echo "run              - Run the FastAPI application locally"
	@echo "test             - Run unit tests"
	@echo "test-integration - Run PostgreSQL integration tests"
	@echo "docker-up        - Start Docker Compose services and build"
	@echo "docker-down      - Stop Docker Compose services"
	@echo "docker-clean     - Stop Docker Compose services and remove volumes"
	@echo "format           - Format codebase using ruff"
	@echo "lint             - Lint codebase using ruff"
	@echo "clean            - Clean build caches and python artifacts"

init:
	@if [ ! -f .env ]; then cp .env.example .env && echo "Created .env"; else echo ".env already exists"; fi
	@if [ ! -f .env.docker ]; then cp .env.docker.example .env.docker && echo "Created .env.docker"; else echo ".env.docker already exists"; fi

install:
	uv sync
	uv run pre-commit install

run:
	uv run main.py

test:
	uv run python -m pytest -q

test-integration:
	POSTGRES_TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/fortuna \
	uv run python -m pytest tests/test_postgres_integration.py -q

docker-up:
	docker compose --env-file .env.docker up --build

docker-down:
	docker compose --env-file .env.docker down

docker-clean:
	docker compose --env-file .env.docker down -v

format:
	uv run ruff format .

lint:
	uv run ruff check . --fix

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache .venv
	find . -type d -name "__pycache__" -exec rm -r {} +
