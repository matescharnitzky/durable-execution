# LangGraph with PostgreSQL

```sh
make up
make langgraph-run
make langgraph-status
make langgraph-resume
```

All three targets load `.env` and resolve any 1Password references through `scripts/1password.sh`. The default run ID is `report-1`. Reports are saved automatically as `artifacts/langgraph/report_langgraph_<UTC timestamp>.html`. Use a fresh ID for a new run, for example `make langgraph-run RUN_ID=report-2`. Override the filename with `OUTPUT=artifacts/custom.html` when needed. Pass the same `RUN_ID` to status and resume. Use `make up` to start PostgreSQL and pgAdmin. `make down` removes the containers and database volume, including saved checkpoints. Keep PostgreSQL running when stopping and resuming a worker.

`make langgraph-status RUN_ID=<id>` shows the saved turns in a terminal table, plus the current state and next node. Long message contents are shown as previews. Use `STATUS_ARGS=--json` for machine-readable status. The table is reconstructed from LangGraph’s persisted state, so an unfinished API call without a saved result will not appear as a completed turn.

The shared prompt asks the agent to check tomorrow’s date first, then research five cities in order, one city per search. Parallel tool calls are disabled, so each search result returns to the agent before its next call. Resuming continues from the saved checkpoint.

The search tool returns answer text and native citation URLs. Unknown temperatures use `null` and render as “Unavailable”; absent sources render as “No verified source.” Temperature statistics exclude unknown values. A saved final answer can be exported again with `resume` without another model call.

The CLI uses `POSTGRES_USER` and `POSTGRES_PASSWORD` for the local `langgraph` database on port 5432. Checkpoint tables live in its `public` schema. Compose creates the database when initializing a fresh volume. `LANGGRAPH_DATABASE_URL` can override the connection. In pgAdmin at [localhost:80](http://localhost:80), register host `postgres`, port `5432`, and maintenance database `postgres`, then browse **langgraph → Schemas → public → Tables**. See the [root README](../getting-started.md) for environment values and 1Password setup.

To demonstrate a crash, start the services with `make up`, then run:

```sh
./tests/langgraph-crash.sh
```

The script calls the existing Make targets to run, inspect, and resume one execution. The script waits for a saved checkpoint before showing the kill prompt. Inspect Logfire or pgAdmin, then press Enter to kill the run’s process group with `SIGKILL`. Press Enter again to resume the same run ID. PostgreSQL stays running. You can supply a run ID as the script’s first argument. Credentials are resolved once for the demo and reused by its Make commands. This uses real OpenAI calls; crash timing is manual, and an unfinished API call may be repeated.

The CLI configures LangChain’s `create_agent` with the shared system prompt, PostgreSQL checkpointer, and the OpenAI web-search tool from `tools.py`. `config.py` loads the model, database URL, and credentials from the environment. The shared `weather_core.report` renderer exports the forecast with `experiment="LangGraph"`. Its HTML template lives in core. The HTML report is self-contained and adapts to desktop, mobile, and print. Run and resume generate a new timestamped filename by default; `--output` overrides the path.

## Observe a run

Set `LOGFIRE_TOKEN` and run or resume the graph. LangGraph’s native tracer sends agent and model spans through Logfire's OpenTelemetry provider. `observability.py` sets the documented LangSmith tracing environment variables before running the agent and then calls `logfire.configure()`. It uses OpenTelemetry-only mode with inputs and outputs hidden. No LangSmith account or API key is needed. The agent calls a LangChain tool that runs OpenAI-hosted search. Filter by `langsmith.metadata.durable.run_id` to see activity across restarts. Use `status` and pgAdmin for persisted checkpoint state, and Logfire to inspect model and tool activity across restart.

[Logfire's LangGraph integration](https://pydantic.dev/docs/logfire/integrations/llms/langgraph/)
