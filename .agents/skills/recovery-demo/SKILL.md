---
name: recovery-demo
description: Run and document the lab's durable execution crash demonstrations.
---

# Recovery demo

Use the runtime's README and existing Make commands. Start services separately with `make up`. Keep PostgreSQL running and preserve the original run ID across worker replacement; `make down` deletes checkpoints.

For LangGraph, run `./tests/langgraph-crash.sh`. It calls Make to start the execution, kills that run's process group with `SIGKILL` when Enter is pressed, shows status, and resumes the same run after another Enter. It uses real OpenAI calls, so confirm which model or tool steps completed in Logfire or native checkpoint history before killing it. Timing is manual; do not claim a specific crash boundary without observing it.

Compare the persisted messages and next node before and after resume. Record which results were reused, which unfinished work ran again, whether the report finished, and anything the evidence cannot establish. Do not infer exact provider request counts from checkpoint row counts or missing traces. Keep credentials and raw model payloads out of shared evidence.

HTTP 429 and lost-response injection are outside this crash script's scope. Only report those scenarios as verified when separate evidence exists.
