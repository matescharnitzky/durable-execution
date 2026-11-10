.PHONY: setup check

setup:
	uv sync --locked --all-packages
	npm ci --ignore-scripts

check:
	uv run --locked --package weather-report python -m unittest discover -s shared/tests
