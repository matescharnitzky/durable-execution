# Pydantic AI with DBOS

Start the services separately with `make up`, then:

```sh
make dbos-run RUN_ID=report-1
make dbos-status RUN_ID=report-1
make dbos-resume RUN_ID=report-1
```

Use a fresh ID for each new execution. The shared prompt asks for tomorrow’s forecast for 20 cities. Pydantic AI uses OpenAI’s native web-search tool and structured output with the shared report schema. Reports use the core HTML renderer and are saved under `artifacts/dbos/report_dbos_<UTC timestamp>.html`. Set `OUTPUT` to override the path.

DBOS uses the PostgreSQL credentials from `.env` and its own `dbos` schema in `weather`. `DBOS_SYSTEM_DATABASE_URL` overrides the connection. The runtime creates and migrates its own tables. In pgAdmin, browse **weather → Schemas → dbos → Tables**.

## Crash and resume

```sh
./tests/dbos-crash.sh
```

The script calls Make to run, inspect, and resume the same workflow. It waits until DBOS has stored the workflow before offering to kill its local process group. PostgreSQL stays running. Use Logfire or pgAdmin to choose when to press Enter. The script uses real OpenAI calls and resolves 1Password credentials once for the whole demo; its nested Make commands reuse that environment.

DBOS records Pydantic AI model requests as durable steps. Completed steps are reused when the workflow replays. Hosted web searches inside an unfinished model request can run again. `status` shows the native saved steps and their output previews; `STATUS_ARGS=--json` returns machine-readable state. `resume` uses DBOS’s native workflow recovery, preserving the workflow ID. Completed workflows can export their saved report again.

## Logfire

Set `LOGFIRE_TOKEN` in `.env`. Pydantic AI’s native instrumentation emits model spans with content disabled, and the workflow span carries `durable.runtime=dbos` and `durable.run_id`. Correlate traces with the workflow ID and compare them with native DBOS step history.

[Pydantic AI’s DBOS integration](https://pydantic.dev/docs/ai/capabilities/durable_execution/dbos/)
