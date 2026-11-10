# Pydantic AI with DBOS

Start PostgreSQL with `docker compose up -d --wait postgres`. On a fresh local volume, create the DBOS system database once with `docker compose exec -T postgres createdb -U weather weather_dbos`. Set `DBOS_SYSTEM_DATABASE_URL` to use another database.

```sh
uv run --locked dbos-report run report-2 --date YYYY-MM-DD --output artifacts/dbos.html
uv run --locked dbos-report status report-2
uv run --locked dbos-report resume report-2 --output artifacts/dbos.html
uv run --locked python tests/recovery/demo.py .venv/bin/dbos-report
```

Each batch is one Pydantic AI model turn backed by the shared OpenAI Responses call. Hosted web search happens inside that turn. The DBOS integration records the turn as a model step. After worker death, DBOS launch recovered the original workflow and reused A. DBOS step retries handled both the 429 and lost response. The fixture recorded A, B, B in all three scenarios. The status command reads DBOS workflow and step metadata without starting a worker.
