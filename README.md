# Durable execution lab

Compare what LangGraph, Pydantic AI with DBOS, Pydantic AI with Temporal, and Pi Durable recover when a weather report run is interrupted.

## Setup and checks

Use Python from `.python-version` (installed by uv), Node from `.nvmrc`, and uv 0.13.5. If you use nvm, run `nvm install` from the repo root.

```sh
make setup
make check
```

The smoke check verifies the test report against the report schema. It runs without Docker or provider credentials. GitHub Actions uses the same commands.

For Codex Cloud, create an environment for `matescharnitzky/durable-execution` using those Node and uv versions. Set the setup script to `make setup`. Run `make check` in a fresh task on the branch you want to verify. Dependency installation needs access to the Python and npm package registries. The checked-in Codex environment also exposes setup and check actions for local worktrees.

## Report contract

Core holds the system prompt and report schema. Test data lives under `core/tests`. The live workload covers 20 cities and requests tomorrow’s forecast. The prompt includes the city list. LangGraph uses a web search tool before generating the full report. DBOS, Temporal, and Pi use four batches of five. Each forecast includes the city, low and high temperatures in Celsius, conditions, and clickable source links. Render a single HTML report with the forecast date, summary, and one forecast per requested city in input order. Escape forecast text and citation labels before rendering.

The runtime integrations use their own OpenAI clients to call Responses with hosted web search for live forecasts. The runtime owns persistence for unfinished work. The fault-injection endpoint's request log serves as evidence alongside native runtime history.

## Local runtime configuration

The CLI uses local Compose services where needed. LangGraph and DBOS use local PostgreSQL, with separate databases for their runtime state. Temporal uses a local server, and Pi Durable uses a local SQLite file. pgAdmin can be used to inspect PostgreSQL.

For live runs, copy `.env.example` to the ignored `.env`. Use plain values or `op://` field references from the `durable-execution` item in the 1Password Development vault. For references, install the 1Password CLI and enable its desktop app integration. Use **Copy Secret Reference** in 1Password to get the exact field names. The OpenAI key covers both model calls and hosted web search.

```sh
make up
make langgraph-run RUN_ID=report-1
make langgraph-status RUN_ID=report-1
make langgraph-resume RUN_ID=report-1
make down
```

The Make targets use `scripts/1password.sh` to resolve references when present. Plain `.env` values and exported environment variables work without 1Password. Start PostgreSQL with `make up` before running the report commands. `make down` removes the containers and database volume, including saved checkpoints. Keep PostgreSQL running while testing worker crash recovery.

To wrap another command directly, use `./scripts/1password.sh <command>`. For Python commands that should also load plain `.env` values, use `./scripts/1password.sh uv run --env-file .env --locked <command>`.

## Telemetry

Runtime integrations send to Logfire when `LOGFIRE_TOKEN` is configured. Use native framework instrumentation where available and OpenTelemetry for Pi Durable. Correlate model calls, tool calls, and recovery events using `durable.runtime` and `durable.run_id`. Add `durable.batch` and `durable.attempt` where the runtime exposes them. Preserve the logical run ID across restarts even when traces differ. Keep credentials and raw prompts and responses out of telemetry by default. Native runtime history and the fixture request log are the recovery evidence.

## Runtimes

- [LangGraph with PostgreSQL](packages/langgraph/README.md)
