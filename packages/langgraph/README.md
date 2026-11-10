# LangGraph with PostgreSQL

```sh
docker compose up -d --wait postgres
uv run --locked langgraph-report run report-1 --date YYYY-MM-DD --output artifacts/report.html
uv run --locked langgraph-report status report-1
uv run --locked langgraph-report resume report-1 --output artifacts/report.html
```

The CLI defaults to the Compose development database. Set `LANGGRAPH_DATABASE_URL` if using different database settings. The `pgadmin` Compose profile exposes pgAdmin on port 55080. Wrap live CLI commands with the [root README's 1Password invocation](../../README.md#local-runtime-configuration).

Run the credential-free recovery demo with `uv run --locked python tests/recovery/demo.py .venv/bin/langgraph-report`. In all three scenarios, the observed batch order was A, B, B and the original run produced a report. After worker death, `resume` loaded the PostgreSQL checkpoint with A already present. LangChain’s model retry middleware handled the 429 and dropped response without a restart. `status` reports the number of completed batches and the next checkpointed node. Use that with the demo's independent request log.

`graph.py` configures LangChain’s `create_agent` with the report state, shared system prompt, PostgreSQL checkpointer, and the OpenAI web-search tool from `tools.py`. `config.py` loads the model, database URL, and credentials from the environment.

## Observe a run

Set `LOGFIRE_TOKEN` and run or resume the graph. LangGraph’s native tracer sends agent, middleware, and model spans through Logfire's OpenTelemetry provider. `observability.py` sets the documented LangSmith tracing environment variables before importing LangGraph and then calls `logfire.configure()`. It uses OpenTelemetry-only mode with inputs and outputs hidden. No LangSmith account or API key is needed. Hosted search runs inside the model request. Filter by `langsmith.metadata.durable.run_id` to see activity across restarts. Use `status` for the persisted checkpoint state and the fixture log for the exact HTTP attempts.

[Logfire's LangGraph integration](https://pydantic.dev/docs/logfire/integrations/llms/langgraph/)
