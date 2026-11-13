# Getting started

Run all commands from the repository root.

## Install

Install uv 0.13.5, Node matching `.nvmrc`, and Docker with Compose.
Python is pinned in `.python-version` and installed by uv. If using nvm, run `nvm install`.

```sh
make install
make check
```

Checks require no provider credentials. They run Ruff, Pyright, Biome, ShellCheck,
pytest, TypeScript checking, and the Node recovery tests.

## Configure live runs

Copy `.env.example` to `.env` without overwriting an existing configuration.
Set `OPENAI_API_KEY`, `PGADMIN_EMAIL`, and `PGADMIN_PASSWORD`. Database credentials
use local defaults unless `POSTGRES_USER` and `POSTGRES_PASSWORD` override them.
`LOGFIRE_TOKEN` enables optional tracing; `LOGFIRE_BASE_URL` selects its region when needed.
Never commit secrets or paste them into logs.

Plain values and exported variables work. For 1Password, install its CLI, enable desktop
integration, and use `op://` references. Make commands resolve references through
`scripts/1password.sh`. With multiple accounts, set `OP_ACCOUNT` to the sign-in address
or account ID; an exported value takes precedence over `.env`.

## Start infrastructure

```sh
make up
```

Compose starts Postgres, pgAdmin, Temporal, its schema/namespace initialization jobs,
and Temporal UI. pgAdmin is at `http://localhost:80`; Temporal UI is at
`http://localhost:8233`. These are local development addresses.

The Temporal application worker runs separately with `make temporal-worker`.
Pi uses SQLite and does not require Docker.

Use the [runtime guides](runtimes/langgraph.md) for run/status/resume commands.
Each new run needs a fresh `RUN_ID`; use the same ID when recovering it.
Reports are written below `artifacts/<runtime>/`; set `OUTPUT` to override the path.

**Destructive cleanup:** `make down` removes database volumes and their saved runs.
Use `docker compose stop` when you only want to stop infrastructure and retain data.

## Preview and build documentation

```sh
make docs-serve
make docs-build
```

The preview serves locally on port 8000. The build writes static files to `site/`,
which is ignored by Git. Both commands install the locked docs dependency group as needed.
CI builds the documentation; it does not publish a website.
