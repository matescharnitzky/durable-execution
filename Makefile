.PHONY: setup check

setup:
	uv sync --locked --all-packages
	npm ci --ignore-scripts

check:
	uv run --locked --package weather-core python -m unittest discover -s core/tests
	npm exec --workspace @durable-execution/pi-durable -- tsc --noEmit

.PHONY: recovery
recovery:
	.venv/bin/python tests/recovery/demo.py .venv/bin/langgraph-report --search-tool
	.venv/bin/python tests/recovery/demo.py .venv/bin/dbos-report
	.venv/bin/python tests/recovery/demo.py .venv/bin/temporal-report --worker .venv/bin/temporal-report-worker
	.venv/bin/python tests/recovery/demo.py 'node packages/pi-durable/src/cli.ts'
