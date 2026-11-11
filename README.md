# Durable execution lab

Compare how LangGraph, Pydantic AI with DBOS, Pydantic AI with Temporal, and Pi Durable recover interrupted weather report runs.

## Setup

Install uv 0.13.5, Node from `.nvmrc`, and Docker with Compose. uv installs Python from `.python-version`. If you use nvm, run `nvm install`.

```sh
make setup
make check
```

Copy `.env.example` to `.env` if you haven't configured it yet. Set `OPENAI_API_KEY`, `PGADMIN_EMAIL`, and `PGADMIN_PASSWORD`, plus optionally `LOGFIRE_TOKEN`. Set `POSTGRES_USER` and `POSTGRES_PASSWORD` to use your database credentials; otherwise local defaults apply. The OpenAI key covers both model calls and web search.

Plain values, exported variables, and `op://` references are supported. For 1Password, install its CLI, enable desktop app integration, and use field references from the `durable-execution` item in the Development vault. Make targets resolve them through `scripts/1password.sh`.

## LangGraph

Start PostgreSQL and pgAdmin, then generate tomorrow’s forecast for five cities:

```sh
make up
make langgraph-run RUN_ID=report-1
```

LangGraph stores checkpoints in `weather.langgraph` on `localhost:5432`; pgAdmin is available at [localhost:80](http://localhost:80).

Reports are saved as `artifacts/langgraph/report_langgraph_<UTC timestamp>.html`. Use a fresh run ID for each new execution. Set `OUTPUT=artifacts/custom.html` to choose a filename.

Inspect or resume the same execution after stopping its worker:

```sh
make langgraph-status RUN_ID=report-1
make langgraph-resume RUN_ID=report-1
```

Keep PostgreSQL running during recovery. When finished, `make down` removes containers and volumes, including checkpoints.

See [LangGraph details](packages/langgraph/README.md) for the recovery demo and Logfire tracing.

## DBOS

```sh
make dbos-run RUN_ID=report-1
make dbos-status RUN_ID=report-1
make dbos-resume RUN_ID=report-1
```

Start services with `make up` first. DBOS uses the `weather.dbos` schema and saves reports under `artifacts/dbos/`. See [DBOS details](packages/pydantic-dbos/README.md) for its crash demo and native recovery behavior.

## Temporal

Start services with `make up`, then run `make temporal-worker` in another terminal.

```sh
make temporal-run RUN_ID=report-1
make temporal-status RUN_ID=report-1
make temporal-resume RUN_ID=report-1
```

Reports go to `artifacts/temporal/`. See [Temporal details](packages/pydantic-temporal/README.md) for the worker-crash demo and native history.
