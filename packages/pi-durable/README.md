# Pi Durable

```sh
make pi-run RUN_ID=report-1
make pi-status RUN_ID=report-1
make pi-resume RUN_ID=report-1
```

Pi uses a local SQLite file per run under `artifacts/pi/state/`; it does not need Docker. The shared prompt asks for tomorrow’s forecast for 20 cities. All implementations use the same core schema and HTML renderer. Pi passes its final JSON to the core Python CLI and saves `artifacts/pi/report_pi_<UTC timestamp>.html`. `OUTPUT` overrides the filename.

The pinned Pi AI Responses adapter has no first-class hosted web-search option. `provider.ts` uses its supported `onPayload` hook to add OpenAI’s native search tool and strict JSON schema. OpenAI rejects the schema’s `uri` format, so the request omits that keyword; core still validates URLs against the full schema. It preserves the original transcript and native default retry settings. `config.ts` owns the model setting and reads the same prompt and schema resources as Python.

## Crash and resume

```sh
./tests/pi-crash.sh
```

The script uses Make to run, inspect, and resume one execution. It waits for a stored submission before offering to kill the local process group. Credentials are resolved once for the whole demo. This uses real OpenAI calls; timing is manual.

`resume` reopens the same SQLite store, reacquires the original native submission, and resumes the harness. A model request interrupted by a crash becomes a failed attempt and is retried according to Pi’s defaults. Completed submissions export their saved answer without a new model call. Hosted searches within an unfinished model request can repeat.

`status` opens the harness read-only, shows its persisted transcript as a terminal table, and reports the native submission state. `STATUS_ARGS=--json` returns machine-readable status. `PI_STATE_DIR` overrides the store directory.

## Logfire and checks

`LOGFIRE_TOKEN` enables a content-free adapter from Pi’s native telemetry interface to OpenTelemetry. It uses `LOGFIRE_BASE_URL` when configured and attaches `durable.runtime=pi` and the run ID. No model payloads are added to spans.

The credential-free Node test starts the real CLI and SQLite harness with a mocked model transport, kills the process mid-request, reopens the store, checks the original submission ID, and exports HTML through core. It also verifies that a completed submission can export again without another model request.

Live OpenAI recovery was verified on 2026-11-11 with `pi-live-crash-20261111-1`: native submission 8 was placed, generation task 9 was running, SIGKILL stopped the worker, and resume continued the same task on attempt 2. The saved answer contained 20 populated city forecasts and passed core validation. Exporting it again succeeded with the provider URL set to an unreachable local address. Logfire accepted native spans for the run; an exporter observer recorded acceptance and attribute names without recording payloads or credentials.

Recovery does not guarantee forecast quality. A separate uninterrupted live run returned 20 rows but marked 17 unavailable with zero temperatures, which the structural schema accepts. Forecast accuracy and source quality have not been independently checked.

[Pi Durable documentation](https://github.com/earendil-works/pi/blob/main/packages/durable/README.md)
