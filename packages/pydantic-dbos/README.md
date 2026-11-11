# Pydantic AI with DBOS

Start the services separately with `make up`, then:

```sh
make dbos-run RUN_ID=report-1
make dbos-status RUN_ID=report-1
make dbos-resume RUN_ID=report-1
```

Use a fresh ID for each new execution. The shared prompt asks the agent to check tomorrow’s date first, then research five cities in order, with one city per search and a model turn between searches. Parallel function calls are disabled through the model’s native setting. The main Pydantic AI agent calls a `web_search` function tool, which uses OpenAI’s hosted search in a separate request. The final answer uses strict structured output with the shared report schema. Reports use the core HTML renderer and are saved under `artifacts/dbos/report_dbos_<UTC timestamp>.html`. Set `OUTPUT` to override the path.

DBOS uses `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` from `.env`, connects on localhost port 5432, and stores its tables in the `dbos` schema. The runtime creates and migrates its own tables. In pgAdmin, browse **weather → Schemas → dbos → Tables**.

## Crash and resume

```sh
./tests/dbos-crash.sh
```

The script calls Make to run, inspect, and resume the same workflow. It waits until DBOS has stored the workflow before offering to kill its local process group. PostgreSQL stays running. Use Logfire or pgAdmin to choose when to press Enter. The script uses real OpenAI calls and resolves 1Password credentials once for the whole demo; its nested Make commands reuse that environment.

DBOS records each main-agent model request as a durable step. The `web_search` function has its own `@DBOS.step()` boundary, so completed searches are reused and returned to subsequent model turns when the workflow replays. A search interrupted before its step completes can run again. The agent chooses its queries; there is no application-controlled city batching or progress cache.

Search results include the answer and native provider citations so source URLs reach the main agent. The shared report schema allows unknown temperatures as `null` and missing sources as an empty list. HTML shows these as “Unavailable” and “No verified source”; unknown values are excluded from temperature statistics. Recovery success does not establish forecast completeness or accuracy.

`status` shows saved model turns and search results with their native step IDs. Before any step completes it prints “No completed steps saved yet.” `STATUS_ARGS=--json` returns machine-readable state. `resume` uses DBOS’s native workflow recovery, preserving the workflow ID. Completed workflows can export their saved report again. Use fresh run IDs for this version; unfinished workflows from the previous single-request implementation need the code version that started them.

## Logfire

Set `LOGFIRE_TOKEN` in `.env`. Logfire is configured before DBOS launches, and DBOS’s native OpenTelemetry instrumentation emits workflow and step spans through that exporter. Pydantic AI adds agent and model spans with content disabled. Its agent metadata carries `durable.runtime=dbos` and `durable.run_id`; DBOS spans identify the workflow with `dbos.operation.workflow_id`. Correlate these with native DBOS step history. No separate exporter credentials are needed.

[Pydantic AI’s DBOS integration](https://pydantic.dev/docs/ai/capabilities/durable_execution/dbos/)

`make check` includes a credential-free recovery test with native DBOS SQLite storage and deterministic model responses. It kills the worker after a completed search while the next model request is in progress. The replacement worker must receive the saved search result without executing that search again. Live runs use PostgreSQL.
