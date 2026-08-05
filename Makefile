.PHONY: setup test lint fmt run docker-up docker-down

setup:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run mypy src

fmt:
	uv run ruff format .
	uv run ruff check --fix .

run:
	uv run python -m rag

docker-up:
	docker compose up --build

docker-down:
	docker compose down
