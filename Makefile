.PHONY: build-docs serve-docs prepare-docs install check lint format test pi-run pi-status pi-resume temporal-run temporal-status temporal-resume temporal-worker dbos-run dbos-status dbos-resume up down postgres langgraph-run langgraph-status langgraph-resume

install:
	uv sync --locked --all-packages
	npm ci --ignore-scripts

check: lint test

lint:
	uv run --all-packages --locked ruff check .
	uv run --all-packages --locked ruff format --check .
	uv run --all-packages --locked pyright
	npm run lint
	uv run --locked shellcheck scripts/*.sh tests/*.sh

format:
	uv run --locked ruff check --fix .
	uv run --locked ruff format .
	npm run format

test:
	uv run --all-packages --locked pytest
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

# Stage only the existing documentation, preserving relative README links.
prepare-docs:
	mkdir -p .cache/docs
	cp README.md .cache/docs/README.md
	@for readme in packages/*/README.md; do \
		mkdir -p ".cache/docs/$$(dirname "$$readme")"; \
		cp "$$readme" ".cache/docs/$$readme"; \
	done

build-docs: prepare-docs
	uv run --locked --group docs zensical build --strict

serve-docs: prepare-docs
	uv run --locked --group docs zensical serve

.PHONY: pgtask-install pgtask-run pgtask-status pgtask-resume pgtask-worker

pgtask-install:
	@./scripts/1password.sh uv run $(UV_ENV_FILE) --locked pgtask-report install

pgtask-run:
	@./scripts/1password.sh uv run $(UV_ENV_FILE) --locked pgtask-report run "$(RUN_ID)" $(if $(OUTPUT),--output "$(OUTPUT)")

pgtask-status:
	@./scripts/1password.sh uv run $(UV_ENV_FILE) --locked pgtask-report status "$(TASK_ID)" $(STATUS_ARGS)

pgtask-resume:
	@./scripts/1password.sh uv run $(UV_ENV_FILE) --locked pgtask-report resume "$(TASK_ID)" $(if $(OUTPUT),--output "$(OUTPUT)")

pgtask-worker:
	@./scripts/1password.sh uv run $(UV_ENV_FILE) --locked pgtask-report worker
