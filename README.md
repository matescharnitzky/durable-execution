# Durable execution lab

Compare what LangGraph, Pydantic AI with DBOS, Pydantic AI with Temporal, and Pi Durable recover when a weather report run is interrupted.

## Setup and checks

Use Python from `.python-version` (installed by uv), Node from `.nvmrc`, and uv 0.13.5. If you use nvm, run `nvm install` from the repo root.

```sh
make setup
make check
```

The smoke check verifies the city list and sample report against the shared contract. It runs without Docker or provider credentials. GitHub Actions uses the same commands.

For Codex Cloud, create an environment for `matescharnitzky/durable-execution` using those Node and uv versions. Set the setup script to `make setup`. Run `make check` in a fresh task on the branch you want to verify. Dependency installation needs access to the Python and npm package registries. The checked-in Codex environment also exposes setup and check actions for local worktrees.

## Report contract

The JSON files under [weather_report/fixtures](shared/src/weather_report/fixtures) are shared by Python and TypeScript. The live workload takes an explicit ISO date and uses four batches of five cities. Each forecast includes the city, low and high temperatures in Celsius, conditions, and clickable source links. Render a single HTML report with the forecast date, summary, and one forecast per requested city in input order. Escape forecast text and citation labels before rendering.

The runtime integrations will call OpenAI Responses with hosted web search for live forecasts. The runtime owns persistence for unfinished work. The fault-injection endpoint's request log serves as evidence alongside native runtime history.

## Local runtime configuration

The CLI uses local Compose services where needed. LangGraph and DBOS use local PostgreSQL, with separate databases for their runtime state. Temporal uses a local server, and Pi Durable uses a local SQLite file. pgAdmin can be used to inspect PostgreSQL.

For live runs, copy `.env.example` to the ignored `.env`. Replace each placeholder with the corresponding `op://` field reference from the `durable-execution` item in the 1Password Development vault. Use **Copy Secret Reference** in 1Password to get the exact field names. Run the relevant adapter command through `op run --env-file=.env -- <command>` to inject the resolved values only into that process. The OpenAI key covers both model calls and hosted web search.

## Telemetry

Runtime integrations send to Logfire when `LOGFIRE_TOKEN` is configured. Use native framework instrumentation where available and OpenTelemetry for Pi Durable. Correlate model calls, tool calls, and recovery events using `durable.runtime` and `durable.run_id`. Add `durable.batch` and `durable.attempt` where the runtime exposes them. Preserve the logical run ID across restarts even when traces differ. Keep credentials and raw prompts and responses out of telemetry by default. Native runtime history and the fixture request log are the recovery evidence.

## LangGraph with PostgreSQL

```sh
docker compose up -d --wait postgres
uv run --locked langgraph-report run report-1 --date YYYY-MM-DD --output artifacts/report.html
uv run --locked langgraph-report status report-1
uv run --locked langgraph-report resume report-1 --output artifacts/report.html
```

The CLI defaults to the Compose development database. Set `LANGGRAPH_DATABASE_URL` if using different database settings. The `pgadmin` Compose profile exposes pgAdmin on port 55080. Wrap live CLI commands with the 1Password invocation above.

Run the credential-free recovery demo with `uv run --locked python tests/recovery/demo.py .venv/bin/langgraph-report`. In all three scenarios, the observed batch order was A, B, B and the original run produced a report. After worker death, `resume` loaded the PostgreSQL checkpoint with A already present. The graph's node retry policy handled the 429 and dropped response without a restart. `status` reports the number of completed batches and the next checkpointed node. Use that with the demo's independent request log.

## Pydantic AI with DBOS

Start PostgreSQL as above. On a fresh local volume, create the DBOS system database once with `docker compose exec -T postgres createdb -U weather weather_dbos`. Set `DBOS_SYSTEM_DATABASE_URL` to use another database.

```sh
uv run --locked dbos-report run report-2 --date YYYY-MM-DD --output artifacts/dbos.html
uv run --locked dbos-report status report-2
uv run --locked dbos-report resume report-2 --output artifacts/dbos.html
uv run --locked python tests/recovery/demo.py .venv/bin/dbos-report
```

Each batch is one Pydantic AI model turn backed by the shared OpenAI Responses call. Hosted web search happens inside that turn. The DBOS integration records the turn as a model step. After worker death, DBOS launch recovered the original workflow and reused A. DBOS step retries handled both the 429 and lost response. The fixture recorded A, B, B in all three scenarios. The status command reads DBOS workflow and step metadata without starting a worker.

## Pydantic AI with Temporal

```sh
docker compose up -d --wait temporal
uv run --locked temporal-report-worker
```

In another terminal, start and inspect the workflow. Give the worker the live OpenAI credentials through 1Password.

```sh
uv run --locked temporal-report run report-3 --date YYYY-MM-DD --output artifacts/temporal.html
uv run --locked temporal-report status report-3
uv run --locked temporal-report resume report-3 --output artifacts/temporal.html
```

After a crash, start a replacement worker with the same settings. The Temporal service stays running. The CLI attaches to the existing workflow ID. The local UI is at `http://127.0.0.1:8233`.

With the server up and any live worker stopped, run `uv run --locked python tests/recovery/demo.py .venv/bin/temporal-report --worker .venv/bin/temporal-report-worker`. The harness starts and replaces the fixture worker. The fixture uses a shorter activity timeout to make a killed worker detectable within the test. All three scenarios produced A, B, B, with native history showing the first activity settled on attempt 1 and the second on attempt 2. Temporal activity retries handled both transport failures. The worker telemetry includes the workflow ID and activity attempt.

## Pi Durable

```sh
node packages/pi-durable/src/cli.ts run report-4 --date YYYY-MM-DD --output artifacts/pi.html
node packages/pi-durable/src/cli.ts status report-4
node packages/pi-durable/src/cli.ts resume report-4 --output artifacts/pi.html
```

Pi uses one native SQLite store per run in `artifacts/pi`. Set `PI_STATE_DIR` to change the location. Use one writer per run. Each batch is a Pi generation with a stable submission request ID. On resume, the harness continues pending work and returns the settled results for completed submissions. The status command reads assistant entries and their task IDs without starting the scheduler.

Run the fixture with `uv run --locked python tests/recovery/demo.py 'node packages/pi-durable/src/cli.ts'`. The harness retried B after the worker kill, 429, and lost response. With a Logfire token, the adapter exports Pi spans and events over OTLP and tags each span with the logical run ID. Metrics and persisted trace-parent propagation are outside this adapter. Set `LOGFIRE_OTLP_TRACES_URL` for a custom trace endpoint.

See the [side-by-side recovery comparison](docs/recovery-comparison.md) for the evidence and commands to run all four demos.
