# Recovery comparison

Every implementation receives the same prompt: check tomorrow’s date, then research Budapest, Vienna, Prague, Warsaw, and Berlin in order, one city per search. All four disable parallel function calls through the model’s native setting, returning each result to the agent before its next search. Native runtime storage owns unfinished executions. The core package validates the final report and renders the same HTML under `artifacts/<experiment>/`.

| Runtime | Native store and recovery unit | What an interrupted execution can reuse | Verification of this implementation |
|---|---|---|---|
| LangGraph | PostgreSQL database `langgraph` (`public` schema); graph checkpoints and pending task writes | Saved messages and completed model/tool results. An unfinished node can run again. | Live report and local process crash/resume verified. |
| Pydantic AI + DBOS | PostgreSQL database `dbos` (native `dbos` schema); workflow, model turns, and `web_search` function steps | Completed model turns and search results during workflow replay. An unfinished search step can repeat. | Live SIGKILL recovery verified; two completed searches were reused without new search calls. |
| Pydantic AI + Temporal | PostgreSQL databases `temporal` and `temporal_visibility`; workflow history, model activities, and function-tool activities | Completed model turns and search results during deterministic replay. The server times out a lost worker’s activity and retries it. | Live five-city worker replacement verified; completed search activity results were reused. |
| Pi Durable | Native SQLite per run; submissions, generation tasks, `pi.tool` tasks, and transcript entries | Committed model turns and function-tool results. The read-only search tool is replay-safe, so an unfinished search can repeat. Completed submissions reuse their saved answer. | Native SQLite SIGKILL tests verify completed-search reuse and unfinished-search restart. A live five-city crash run completed; a second run stopped at exhausted OpenAI credits after worker replacement. |

All four use function tools that call OpenAI hosted search. DBOS marks that function with `@DBOS.step()`, while Temporal’s native Pydantic AI integration automatically wraps function tools as activities. Main-agent model turns have their own framework persistence. Pi registers `web_search` as a native durable tool with `replay: "safe"`. Its supported Responses hooks enable hosted search inside that tool and preserve native citation URLs. A provider may perform several hosted search actions inside one function-tool call; those internal actions are not separate runtime steps.

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

After splitting DBOS search into function steps, `dbos-search-crash-20261111-2` was killed with two search results saved. A temporary observer confirmed those searches were not executed by the replacement worker, and their stored hashes and completion times remained unchanged. The workflow reached SUCCESS with two model steps and 21 search steps, exporting 20 city rows. The agent chose concurrent searches in this run; no application-controlled batching was used. A credential-free SQLite test also verifies that the next model turn receives its saved search result after process replacement.

The final five-city checks used `langgraph-five-city-crash-20261111-3`, `dbos-five-city-crash-20261111-2`, and `temporal-five-city-crash-20261111-2`. Each checked the date first, searched the cities in order with at most one function call per model turn, and reused two completed searches after SIGKILL. Native saved results remained unchanged, and a temporary observer recorded no repeat invocation of those completed queries. All reported URLs matched native provider citations. LangGraph's answer lacked temperatures for Prague and Warsaw; after the renderer accepted explicit unknown values, its saved answer exported successfully with an unreachable provider endpoint. A fresh `dbos-five-city-final-20261111-1` run also verified OpenAI acceptance of the nullable schema and returned five populated forecasts.

Pi’s function-tool implementation was checked with `pi-five-city-crash-20261111-1`: it reused the committed date result, restarted the unfinished city search, and completed five populated forecasts in order with at most one function call per model turn. Its nine final URLs matched native citations in saved tool results, and completed-answer export succeeded with an unreachable provider. Logfire accepted native spans. In `pi-five-city-crash-20261112-2`, two committed tool-result entries were unchanged after SIGKILL and worker replacement, but the next model call failed because OpenAI credits were exhausted; full recovery of that run remains unverified. Two credential-free native SQLite tests verify completed-search reuse and unfinished-search restart, and another checks terminal provider error reporting. Pi status reads committed history entries because its model-context view can synthesize unavailable-result placeholders for unfinished tools.

The local self-hosted Temporal Server now uses the same PostgreSQL instance as LangGraph and DBOS, with separate databases per implementation. A fresh isolated Compose stack verified all four databases, native LangGraph checkpoint reopen, native DBOS workflow persistence, and a Temporal workflow/activity whose saved result and visibility survived PostgreSQL and server restarts. The separate UI returned HTTP 200; the actual Temporal CLI and Pydantic AI worker connected without provider calls. Earlier provider-backed crash evidence above predates this storage-layout change. Recreate local volumes with `make down` and `make up`; existing runs are not migrated.

Timing is manual. These demos do not inject HTTP 429 or lost responses, and checkpoint counts do not establish exact provider request counts. Forecast accuracy and source-page contents were not independently checked. Earlier twenty-city runs exposed zero placeholders for missing data. The current schema permits `null` temperatures and absent sources; the renderer displays gaps explicitly and excludes unknown values from temperature statistics. Models can still return incorrect data, so workflow success is distinct from forecast quality. `make down` deletes the Compose volumes and their stored execution history; Pi’s local SQLite files remain under artifacts.
