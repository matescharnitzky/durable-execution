# Pydantic AI with Temporal

Start the services with `make up`. Start a worker in another terminal:

```sh
make temporal-worker
```

Then run, inspect, or follow the same workflow:

```sh
make temporal-run RUN_ID=report-1
make temporal-status RUN_ID=report-1
make temporal-resume RUN_ID=report-1
```

The shared prompt asks for tomorrow’s forecast for 20 cities. Pydantic AI uses native OpenAI web search, strict structured output, and `TemporalDurability()` with its default activity timeouts and retry policy. The core renderer exports `artifacts/temporal/report_temporal_<UTC timestamp>.html`; `OUTPUT` overrides the path.

The local Temporal development server persists its native history to a Docker volume. Its API is on port 7233 and UI at [localhost:8233](http://localhost:8233). Its native SQLite store is separate from the PostgreSQL schemas used by LangGraph and DBOS. `TEMPORAL_ADDRESS` can override the server connection. `make down` removes the volume and workflow history.

## Crash and resume

Stop any separately started worker before running:

```sh
./tests/temporal-crash.sh
```

The script starts a worker and client through Make, waits for a model activity to start, and asks when to kill both local process groups. Temporal and PostgreSQL stay running. After inspecting the native status table, press Enter to start a replacement worker and follow the original workflow. The script stops its replacement worker when finished.

Temporal resumes automatically once a worker is available and the server detects the old attempt’s timeout. The default model activity heartbeat timeout is 30 seconds, so replacement can take time. Completed activities are reused; a hosted search inside an unfinished model activity can run again. Killing only the CLI client does not kill the worker or cancel the workflow.

`status` shows native activity events, attempts, and saved result previews. `STATUS_ARGS=--json` returns machine-readable state. The demo uses real OpenAI calls and manual timing.

## Logfire

The worker and client load credentials through the same 1Password helper as LangGraph. Set `LOGFIRE_TOKEN` to enable Pydantic AI instrumentation with content disabled and the Temporal SDK’s native OpenTelemetry interceptor. Agent metadata and the client span carry the stable workflow ID.

[Pydantic AI’s Temporal integration](https://pydantic.dev/docs/ai/capabilities/durable_execution/temporal/)
