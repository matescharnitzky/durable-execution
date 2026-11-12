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

The shared prompt asks the agent to check tomorrow’s date first, then research five cities in order, one city per search. Parallel function calls are disabled through the model’s native setting. The main agent calls a `web_search` function tool, which makes a separate OpenAI hosted-search request. `TemporalDurability()` records main-agent model turns and function-tool calls as activities using its default timeouts and retry policy. Strict structured output feeds the core renderer, which exports `artifacts/temporal/report_temporal_<UTC timestamp>.html`; `OUTPUT` overrides the path.

The search tool returns answer text with native provider citations. The shared report contract uses `null` for unknown temperatures and an empty list for missing sources; the HTML renderer shows these gaps explicitly and excludes unknown values from temperature statistics. Workflow completion does not establish forecast accuracy.

The local Temporal development server persists its native history to a Docker volume. Its API is on port 7233 and UI at [localhost:8233](http://localhost:8233). Its native SQLite store is separate from the PostgreSQL schemas used by LangGraph and DBOS. `TEMPORAL_ADDRESS` can override the server connection. `make down` removes the volume and workflow history.

## Crash and resume

Stop any separately started worker before running:

```sh
./tests/temporal-crash.sh
```

The script starts a worker and client through Make, waits for a model activity to start, and asks when to kill both local process groups. Temporal and PostgreSQL stay running. After inspecting the native status table, press Enter to start a replacement worker and follow the original workflow. The script stops its replacement worker when finished. Credentials are resolved once and reused across its Make commands.

Temporal resumes automatically once a worker is available and the server detects the old attempt’s timeout. The default model activity heartbeat timeout is 30 seconds, so replacement can take time. Completed model and search activities are reused; an unfinished search activity can run again. Killing only the CLI client does not kill the worker or cancel the workflow. Use fresh workflow IDs after changing the tool/activity structure; unfinished older workflows need their original code version.

`status` shows native activity events, attempts, and saved result previews. `STATUS_ARGS=--json` returns machine-readable state. The demo uses real OpenAI calls and manual timing.

## Logfire

The worker and client load credentials through the same 1Password helper as LangGraph. Set `LOGFIRE_TOKEN` to enable Pydantic AI’s native `LogfirePlugin` with replay-safe Temporal tracing. `observability.py` configures Logfire and instruments Pydantic AI with content disabled; the plugin owns the Temporal instrumentation. Agent metadata and native Temporal spans identify the workflow. The plugin’s optional Temporal metrics exporter is disabled because the pinned integration uses gRPC against Logfire’s HTTP metrics endpoint; model timing and token usage remain in traces.

`cli.py` defines the Typer arguments and explicitly imports the async `run`, `resume`, `status`, and `worker` functions from `commands.py`. Each callback calls its imported function through `asyncio.run()`. The async `temporal_runtime()` context manager connects the client with the native plugins and flushes telemetry on exit. All SDK operations for a command use that command’s event loop, which `asyncio.run()` closes when it finishes.

[Pydantic AI’s Temporal integration](https://pydantic.dev/docs/ai/capabilities/durable_execution/temporal/)
