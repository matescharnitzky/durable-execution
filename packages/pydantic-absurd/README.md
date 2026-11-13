# Pydantic AI with absurd

Uses the official [Pydantic AI integration](https://pydantic.dev/docs/ai/harness/absurd/)
and [absurd documentation](https://github.com/earendil-works/absurd).
The shared prompt, strict report schema, citations, and HTML renderer match the other runtimes.
Model and search calls are sequential. The search agent runs inside the main agent's durable tool call.

## Setup

Run `make install` and start Postgres with `make up`. Fresh volumes create the `absurd` database;
for existing volumes create that database manually without removing saved runs.
Set `ABSURD_DATABASE_URL` if using non-default PostgreSQL credentials or another server.
Set `OPENAI_API_KEY` for live calls; `OPENAI_MODEL` defaults to `gpt-6-luna`.
`LOGFIRE_TOKEN` optionally enables content-free Pydantic AI tracing.

Install the official Absurd SQL schema before creating the queue: `uvx absurdctl migrate -d "$ABSURD_DATABASE_URL"`.

```sh
make absurd-install
make absurd-worker  # separate terminal; keep running
make absurd-run RUN_ID=report-1
# Copy the printed native Task ID:
make absurd-status TASK_ID=<task-id>
make absurd-resume TASK_ID=<task-id>
```

`RUN_ID` is an enqueue idempotency key; use a fresh value for a new report.
Status and resume take the native task UUID printed before waiting, not the enqueue key.
`STATUS_ARGS=--json` gives machine-readable status. `OUTPUT` overrides the timestamped HTML path.
To recover, keep Postgres intact, kill the worker, then restart `make absurd-worker`.
The engine retries after the claim/lease expires and reuses committed model/tool steps.
Resume follows or exports that same task; it does not create a replacement task or force-retry terminal failures.
Completed reports can be exported again without provider calls while native results remain retained.
Do not change agent/tool names or workflow code for in-flight tasks. An external call interrupted
before its result is checkpointed can repeat and be charged again.
`make down` deletes database volumes and saved runs.

## Validation

Live provider crash recovery requires PostgreSQL and an OpenAI key. Unit tests and type checks
alone do not establish live recovery, request counts, or forecast accuracy.

Run the credential-free native crash test against a dedicated database with the Absurd schema installed:
`ABSURD_TEST_DATABASE_URL=postgresql://... uv run --all-packages pytest packages/pydantic-absurd/tests`.
It uses the real worker and PostgreSQL, kills it after a committed search, replaces it,
and requires replay to succeed with the search transport disabled. Without the test URL it skips.
