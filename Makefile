.PHONY: setup check up down postgres langgraph-run langgraph-status langgraph-resume

setup:
	uv sync --locked --all-packages
	npm ci --ignore-scripts

check:
	uv run --locked --package weather-core python -m unittest discover -s core/tests

UV_ENV_FILE := $(if $(wildcard .env),--env-file .env)

RUN_ID ?= report-1
OUTPUT ?= artifacts/report.html

up:
	@./scripts/1password.sh docker compose up -d --wait postgres

down:
	@./scripts/1password.sh docker compose down --volumes

postgres: up

langgraph-run:
	@./scripts/1password.sh uv run $(UV_ENV_FILE) --locked langgraph-report run "$(RUN_ID)" --output "$(OUTPUT)"

langgraph-status:
	@./scripts/1password.sh uv run $(UV_ENV_FILE) --locked langgraph-report status "$(RUN_ID)"

langgraph-resume:
	@./scripts/1password.sh uv run $(UV_ENV_FILE) --locked langgraph-report resume "$(RUN_ID)" --output "$(OUTPUT)"
