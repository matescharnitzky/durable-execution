# Pydantic AI with Temporal

```sh
docker compose up -d --wait temporal
uv run --locked temporal-report-worker
```

In another terminal, start and inspect the workflow. Give the worker the live OpenAI credentials through 1Password.

```sh
uv run --locked temporal-report run report-3 --date YYYY-MM-DD --output artifacts/temporal.html
uv run --locked temporal-report status report-3
uv run --locked temporal-report resume report-3 --output artifacts/temporal.html
```

The worker uses Pydantic AI’s native OpenAI Responses model and WebSearchTool. Each batch is a model activity, with the original workflow ID preserved across worker replacement.


After a crash, start a replacement worker with the same settings. The Temporal service stays running. The CLI attaches to the existing workflow ID. The local UI is at `http://127.0.0.1:8233`.

With the server up and any live worker stopped, run `uv run --locked python tests/recovery/demo.py .venv/bin/temporal-report --worker .venv/bin/temporal-report-worker`. The harness starts and replaces the fixture worker. The fixture uses a shorter activity timeout to make a killed worker detectable within the test. All three scenarios produced A, B, B, with native history showing the first activity settled on attempt 1 and the second on attempt 2. Temporal activity retries handled both transport failures. The worker telemetry includes the workflow ID and activity attempt.
