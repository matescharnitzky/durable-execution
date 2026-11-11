# Pi Durable

```sh
make pi-run RUN_ID=report-1
make pi-status RUN_ID=report-1
make pi-resume RUN_ID=report-1
```

Pi uses a local SQLite file per run under `artifacts/pi/state/`; it does not need Docker. The same shared prompt as the other implementations asks the agent to check tomorrow’s date, then research five cities in order, one city per function-tool call. Each search result returns to the agent before its next turn. Native sequential tool execution and `parallel_tool_calls=false` enforce serial calls; the application does not loop over cities.

`tools.ts` defines a native Pi Durable `web_search` tool. It calls OpenAI hosted search through Pi AI’s Responses adapter and returns the answer with native URL citations. The pinned adapter needs its supported `onPayload` hook for hosted search and `onProviderStreamEvent` to retain citation annotations. The main model keeps its normal function tools and uses the shared strict report schema. OpenAI’s request omits unsupported URI format; core validates the full schema.

All implementations use the same core prompt resources, schema, and HTML renderer. Pi passes its final JSON to the core Python CLI and saves `artifacts/pi/report_pi_<UTC timestamp>.html`. `OUTPUT` overrides the filename. `config.ts` reads the model setting and shared resources.

## Crash and resume

```sh
./tests/pi-crash.sh
```

The script uses Make to run, inspect, and resume one execution. It waits for a stored submission before offering to kill the local process group. Credentials are resolved once for the whole demo. This uses real OpenAI calls; inspect `make pi-status` or Logfire to choose the crash point.

Pi stores model generations and each function-tool call as native durable tasks. `resume` reopens the same SQLite store, reacquires the original submission, and resumes the harness. Completed search results remain in the agent’s context without executing those tools again. The search tool uses native `replay: "safe"` because searching is read-only: a search interrupted before its result is committed can run again. A request whose response was lost before commit can therefore be charged again. Native model retry defaults are unchanged. Terminal provider failures, such as exhausted credits, are reported with the native error; `resume` does not forcibly retry a terminal submission. Completed submissions export their saved answer without another model or search call.

`status` opens the harness read-only and shows messages from the latest 100 committed native history entries, plus the native submission state. It reads raw entries rather than the model-context view, which can synthesize unavailable-result placeholders for unfinished tools. `STATUS_ARGS=--json` returns machine-readable status. `PI_STATE_DIR` overrides the store directory.

## Logfire and checks

`LOGFIRE_TOKEN` enables a content-free adapter from Pi’s native telemetry interface to OpenTelemetry. It uses `LOGFIRE_BASE_URL` when configured and attaches `durable.runtime=pi` and the run ID. No model payloads are added to spans.

The credential-free tests use the real CLI and native SQLite harness with a mocked model transport. They kill the process after two completed searches and during the next search, then verify that saved results reach the next model turn, completed searches are not repeated, and the unfinished search runs again. Both tests export HTML through core and re-export the completed answer without another provider invocation. They also check serial calls, preserved function tools, citation propagation, and request schema compatibility.

Live OpenAI run `pi-five-city-crash-20261111-1` completed after SIGKILL: a saved date result was reused, the unfinished Budapest search ran again, and the final report contained five populated forecasts. Every model turn made at most one function call; the agent used targeted follow-ups before moving to the next city. All nine final source URLs matched native citations saved in tool results. Exporting the completed answer again succeeded with an unreachable provider endpoint. A temporary observer confirmed Logfire collector acceptance without logging credentials or model payloads.

A second live run, `pi-five-city-crash-20261112-2`, was killed after two successful native tool results were committed. Those entries remained unchanged after worker replacement, but OpenAI rejected the resumed model request because the account had no credits remaining. Its full recovery is therefore unverified. The offline tests verify that boundary without credentials. HTTP 429/lost-response injection and forecast accuracy have not been verified.

[Pi Durable documentation](https://github.com/earendil-works/pi/blob/main/packages/durable/README.md)
