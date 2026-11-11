# Recovery comparison

Every implementation receives the same prompt for tomorrow’s forecasts for 20 cities. Native runtime storage owns unfinished executions. The core package validates the final report and renders the same HTML under `artifacts/<experiment>/`.

| Runtime | Native store and recovery unit | What an interrupted execution can reuse | Verification of this implementation |
|---|---|---|---|
| LangGraph | PostgreSQL `weather.langgraph`; graph checkpoints and pending task writes | Saved messages and completed model/tool results. An unfinished node can run again. | Live report and local process crash/resume verified. |
| Pydantic AI + DBOS | PostgreSQL `weather.dbos`; workflow and model steps | Completed model-step results during workflow replay. Hosted search inside an unfinished request can repeat. | Live report and SIGKILL recovery of the same workflow verified. |
| Pydantic AI + Temporal | Persisted local Temporal server; workflow history and activities | Completed activity results during deterministic replay. The server times out a lost worker’s activity and retries it. | Live report and worker replacement verified; native history showed model activity attempt 2. |
| Pi Durable | Native SQLite per run; submissions, generation tasks, and transcript entries | The original submission and committed transcript. A model request interrupted by a crash is retried; completed submissions reuse their saved answer. | Live OpenAI report and SIGKILL recovery verified; the original submission completed on generation attempt 2. Completed-answer export also succeeded with an unreachable provider URL. |

The implementations expose their normal framework boundaries. LangGraph uses a function tool that calls OpenAI web search. Pydantic AI uses OpenAI’s native search tool within a model request. Pi adds that native tool through its supported Responses payload hook. A hosted search action is not necessarily its own durable runtime step.

## Run the demos

Run `make setup` and `make check`. Start shared services separately with `make up` for LangGraph, DBOS, and Temporal. Pi only needs local files.

```sh
./tests/langgraph-crash.sh
./tests/dbos-crash.sh
./tests/temporal-crash.sh
./tests/pi-crash.sh
```

Run them individually. Each uses real OpenAI calls and resolves 1Password credentials once per demo. Stop any separately running Temporal worker before its demo, which starts and replaces its own worker.

The scripts print the run ID, wait for native persisted state, ask when to send SIGKILL, show native status, and resume the same execution. PostgreSQL and Temporal stay running. Use Logfire, pgAdmin, or Temporal UI to choose the crash point and distinguish saved results from in-flight work. Terminal status tables display persisted messages, steps, or activity events according to the runtime.

Live recovery checks on 2026-11-11 used `dbos-live-audit-20261111-1`, `temporal-live-audit-20261111-1`, and `pi-live-crash-20261111-1`. All completed after SIGKILL and resume. Temporary exporter observers confirmed Logfire collector acceptance for all three without recording credentials or raw payloads. Pydantic AI’s content-disabled message attributes retain roles and part types without prompt or answer text.

Timing is manual. These demos do not inject HTTP 429 or lost responses, and checkpoint counts do not establish exact provider request counts. Forecast accuracy and source quality were not independently checked. One uninterrupted Pi run returned 20 rows but marked 17 unavailable with zero temperatures, which structural validation accepts; the recovered run returned 20 populated rows. `make down` deletes the Compose volumes and their stored execution history; Pi’s local SQLite files remain under artifacts.
