# Recovery and validation

## What recovery reuses

| Runtime | Recovery behavior |
| --- | --- |
| LangGraph | Load the same thread’s checkpoint and continue unfinished graph work |
| DBOS | Recover the workflow and reuse completed step results |
| Temporal | Replay workflow history and reuse completed activity results once a worker is available |
| Pi Durable | Reopen the same SQLite store and reuse committed task results |

An external call whose result was not committed can run again, even if the provider
already performed or charged for it. Side-effecting operations need idempotency or
another deduplication strategy. Keep the original code version for unfinished runs
when changing workflow, activity, or tool structure.

## Credential-free checks

```sh
make check
```

Python tests run under pytest (existing unittest-style cases remain supported).
The DBOS test kills a real local worker and checks recovery using SQLite and deterministic
model responses. Node tests exercise Pi’s CLI, native SQLite storage, process termination,
and deterministic model transport. Temporal unit tests validate CLI dispatch and event-loop
ownership; they do not establish live Temporal activity recovery.

Lint and type checks are also available with `make lint`; `make test` runs Python and
Node tests plus TypeScript checking. `make format` applies Python and JavaScript formatting.

## Live crash demos

After configuring provider credentials and starting the required services:

```sh
./tests/langgraph-crash.sh
./tests/dbos-crash.sh
./tests/temporal-crash.sh
./tests/pi-crash.sh
```

Run one demo at a time. They use real paid OpenAI calls and prompt for manual crash timing.
Stop any separately running Temporal worker before the Temporal crash script, which manages
its own worker. Keep infrastructure and saved stores intact during recovery.

Use runtime status commands to identify completed work before killing a process and inspect
it after recovery. A successful report export proves execution completed, not that the
forecast is accurate. See the runtime guides for specific guarantees and known limitations.
