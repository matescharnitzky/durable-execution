# Pi Durable

```sh
node packages/pi-durable/src/cli.ts run report-4 --date YYYY-MM-DD --output artifacts/pi.html
node packages/pi-durable/src/cli.ts status report-4
node packages/pi-durable/src/cli.ts resume report-4 --output artifacts/pi.html
```

Pi uses one native SQLite store per run in `artifacts/pi`. Set `PI_STATE_DIR` to change the location. Use one writer per run. Each batch is a Pi generation with a stable submission request ID. On resume, the harness continues pending work and returns the settled results for completed submissions. The status command reads assistant entries and their task IDs without starting the scheduler.

Run the fixture with `uv run --locked python tests/recovery/demo.py 'node packages/pi-durable/src/cli.ts'`. The harness retried B after the worker kill, 429, and lost response. With a Logfire token, the adapter exports Pi spans and events over OTLP and tags each span with the logical run ID. Metrics and persisted trace-parent propagation are outside this adapter. Set `LOGFIRE_OTLP_TRACES_URL` for a custom trace endpoint.

See the [side-by-side recovery comparison](../../docs/recovery-comparison.md) for the evidence and commands to run all four demos.
