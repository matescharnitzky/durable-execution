.PHONY: setup check postgres langgraph-run langgraph-status langgraph-resume

setup:
	uv sync --locked --all-packages
	npm ci --ignore-scripts

check:
	uv run --locked --package weather-core python -m unittest discover -s core/tests

RUN_ID ?= report-1
OUTPUT ?= artifacts/report.html

postgres:
	docker compose up -d --wait postgres

langgraph-run: postgres
	op run --env-file=.env -- uv run --locked langgraph-report run "$(RUN_ID)" --output "$(OUTPUT)"

langgraph-status:
	op run --env-file=.env -- uv run --locked langgraph-report status "$(RUN_ID)"

langgraph-resume: postgres
	op run --env-file=.env -- uv run --locked langgraph-report resume "$(RUN_ID)" --output "$(OUTPUT)"
