# Architecture

## Shared contract

`packages/core` owns the prompt, JSON schema, validation, and HTML renderer.
Each runtime keeps orchestration and persistence in its own package and uses the
shared contract. Unknown temperatures are `null`; missing sources are empty lists.
The renderer displays these gaps rather than inventing weather data.

## Execution and storage

| Runtime | Application process | Saved state in this demo |
| --- | --- | --- |
| LangGraph | Python CLI | Postgres `langgraph` database, graph checkpoints |
| Pydantic AI + DBOS | Python CLI | Postgres `dbos` database, workflow and step results |
| Pydantic AI + Temporal | Python client and separate Python worker | Temporal history backed by Postgres `temporal` and `temporal_visibility` databases |
| Pi Durable | Node CLI | SQLite file per run under `artifacts/pi/state/` |

Temporal Server coordinates tasks; your application worker executes workflow and activity code.
Compose runs the server and Postgres, while `make temporal-worker` starts the worker outside Docker.
Other runtimes execute in the CLI process without a separate orchestration server.

Model calls and hosted searches use OpenAI. Each search is a function-tool call,
with its result returned before the agent proceeds. The runtimes retain completed
work through their native persistence mechanisms rather than a shared application cache.

## Observability

Native status commands show persisted state. Optional Logfire tracing helps explain
what ran across process restarts. Traces disable model content; native stores can contain
messages and tool results, so protect them and avoid publishing sensitive run artifacts.
SQLite files need persistent storage and backups if local runs must outlive the machine.
