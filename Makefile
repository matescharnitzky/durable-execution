.PHONY: setup check

setup:
	uv sync --locked --all-packages
	npm ci --ignore-scripts

check:
	uv run --locked --package weather-core python -m unittest discover -s core/tests
