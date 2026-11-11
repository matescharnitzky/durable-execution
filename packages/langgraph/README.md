# LangGraph with PostgreSQL

```sh
make up
make langgraph-run
make langgraph-status
make langgraph-resume
```

All three targets load `.env` and resolve any 1Password references through `scripts/1password.sh`. The defaults are `RUN_ID=report-1` and `OUTPUT=artifacts/report.html`. Use a fresh ID for a new run, for example `make langgraph-run RUN_ID=report-2 OUTPUT=artifacts/report-2.html`. Pass the same `RUN_ID` to status and resume. Use `make up` to start PostgreSQL. `make down` removes the containers and database volume, including saved checkpoints. Keep PostgreSQL running when stopping and resuming a worker.

The shared prompt asks for tomorrow’s forecast for the listed cities. The agent determines the date through web search. Resuming continues from the saved checkpoint.

The CLI defaults to the Compose development database. Set `LANGGRAPH_DATABASE_URL` if using different database settings. The `pgadmin` Compose profile exposes pgAdmin on port 55080. See the [root README](../../README.md#local-runtime-configuration) for plain environment values and 1Password setup.

Run the credential-free demo with `uv run --locked python tests/recovery/demo.py .venv/bin/langgraph-report --search-tool`. The fixture completes web search, then injects a fault during the final model call. After a worker kill, `resume` uses the original PostgreSQL thread ID and reuses the saved search result. The OpenAI client retries a one-time 429 or dropped connection within the same process.

The CLI configures LangChain’s `create_agent` with the shared system prompt, PostgreSQL checkpointer, and the OpenAI web-search tool from `tools.py`. `config.py` loads the model, database URL, and credentials from the environment. The HTML report is written to the file you pass to `--output`, such as `artifacts/report.html`.

## Observe a run

Set `LOGFIRE_TOKEN` and run or resume the graph. LangGraph’s native tracer sends agent and model spans through Logfire's OpenTelemetry provider. `observability.py` sets the documented LangSmith tracing environment variables before running the agent and then calls `logfire.configure()`. It uses OpenTelemetry-only mode with inputs and outputs hidden. No LangSmith account or API key is needed. The agent calls a LangChain tool that runs OpenAI-hosted search. Filter by `langsmith.metadata.durable.run_id` to see activity across restarts. Use `status` for the persisted checkpoint state and the fixture log for the exact HTTP attempts.

[Logfire's LangGraph integration](https://pydantic.dev/docs/logfire/integrations/llms/langgraph/)
