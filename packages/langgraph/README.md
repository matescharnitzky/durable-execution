# LangGraph with PostgreSQL

```sh
docker compose up -d --wait postgres
uv run --locked langgraph-report run report-1 --date YYYY-MM-DD --output artifacts/report.html
uv run --locked langgraph-report status report-1
uv run --locked langgraph-report resume report-1 --output artifacts/report.html
```

The CLI defaults to the Compose development database. Set `LANGGRAPH_DATABASE_URL` if using different database settings. The `pgadmin` Compose profile exposes pgAdmin on port 55080. Wrap live CLI commands with the [root README's 1Password invocation](../../README.md#local-runtime-configuration).

Run the credential-free demo with `uv run --locked python tests/recovery/demo.py .venv/bin/langgraph-report --single-request`. Each scenario makes two attempts at the full report. After a worker kill, `resume` uses the original PostgreSQL thread ID and reruns the pending model call. For a one-time 429 or a dropped connection, the OpenAI client retries within the same process. `status` shows the pending checkpoint nodes.

`graph.py` configures LangChain’s `create_agent` with the shared system prompt, PostgreSQL checkpointer, and the OpenAI web-search tool from `tools.py`. `config.py` loads the model, database URL, and credentials from the environment. Use a fresh run ID for this setup if you previously ran the batched demo.

## Observe a run

Set `LOGFIRE_TOKEN` and run or resume the graph. LangGraph’s native tracer sends agent and model spans through Logfire's OpenTelemetry provider. `observability.py` sets the documented LangSmith tracing environment variables before importing LangGraph and then calls `logfire.configure()`. It uses OpenTelemetry-only mode with inputs and outputs hidden. No LangSmith account or API key is needed. Hosted search runs inside the model request. Filter by `langsmith.metadata.durable.run_id` to see activity across restarts. Use `status` for the persisted checkpoint state and the fixture log for the exact HTTP attempts.

[Logfire's LangGraph integration](https://pydantic.dev/docs/logfire/integrations/llms/langgraph/)
