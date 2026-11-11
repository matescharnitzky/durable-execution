.PHONY: setup check pi-run pi-status pi-resume temporal-run temporal-status temporal-resume temporal-worker dbos-run dbos-status dbos-resume up down postgres langgraph-run langgraph-status langgraph-resume

setup:
	uv sync --locked --all-packages
	npm ci --ignore-scripts

check:
	uv run --locked --package weather-core python -m unittest discover -s core/tests
	uv run --locked --package langgraph-report python -m unittest discover -s packages/langgraph/tests
	uv run --locked --package dbos-report python -m unittest discover -s packages/pydantic-dbos/tests
	uv run --locked --package temporal-report python -m unittest discover -s packages/pydantic-temporal/tests
	npm exec --workspace @durable-execution/pi-durable -- tsc --noEmit
	node --test packages/pi-durable/tests/recovery.test.mjs

UV_ENV_FILE := $(if $(wildcard .env),--env-file .env)

RUN_ID ?= report-1
OUTPUT ?=
STATUS_ARGS ?=

up:
	@./scripts/1password.sh docker compose up -d --wait

down:
	@./scripts/1password.sh docker compose down --volumes

postgres: up

langgraph-run:
	@./scripts/1password.sh uv run $(UV_ENV_FILE) --locked langgraph-report run "$(RUN_ID)" $(if $(OUTPUT),--output "$(OUTPUT)")

langgraph-status:
	@./scripts/1password.sh uv run $(UV_ENV_FILE) --locked langgraph-report status "$(RUN_ID)" $(STATUS_ARGS)

langgraph-resume:
	@./scripts/1password.sh uv run $(UV_ENV_FILE) --locked langgraph-report resume "$(RUN_ID)" $(if $(OUTPUT),--output "$(OUTPUT)")

dbos-run:
	@./scripts/1password.sh uv run $(UV_ENV_FILE) --locked dbos-report run "$(RUN_ID)" $(if $(OUTPUT),--output "$(OUTPUT)")

dbos-status:
	@./scripts/1password.sh uv run $(UV_ENV_FILE) --locked dbos-report status "$(RUN_ID)" $(STATUS_ARGS)

dbos-resume:
	@./scripts/1password.sh uv run $(UV_ENV_FILE) --locked dbos-report resume "$(RUN_ID)" $(if $(OUTPUT),--output "$(OUTPUT)")

temporal-run:
	@./scripts/1password.sh uv run $(UV_ENV_FILE) --locked temporal-report run "$(RUN_ID)" $(if $(OUTPUT),--output "$(OUTPUT)")

temporal-status:
	@./scripts/1password.sh uv run $(UV_ENV_FILE) --locked temporal-report status "$(RUN_ID)" $(STATUS_ARGS)

temporal-resume:
	@./scripts/1password.sh uv run $(UV_ENV_FILE) --locked temporal-report resume "$(RUN_ID)" $(if $(OUTPUT),--output "$(OUTPUT)")

temporal-worker:
	@./scripts/1password.sh uv run $(UV_ENV_FILE) --locked temporal-report worker

pi-run:
	@./scripts/1password.sh node --env-file-if-exists=.env packages/pi-durable/src/cli.ts run "$(RUN_ID)" $(if $(OUTPUT),--output "$(OUTPUT)")

pi-status:
	@./scripts/1password.sh node --env-file-if-exists=.env packages/pi-durable/src/cli.ts status "$(RUN_ID)" $(STATUS_ARGS)

pi-resume:
	@./scripts/1password.sh node --env-file-if-exists=.env packages/pi-durable/src/cli.ts resume "$(RUN_ID)" $(if $(OUTPUT),--output "$(OUTPUT)")
