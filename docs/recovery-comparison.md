# Recovery comparison

The fixtures cover the same two cities. LangGraph sends one report request and the endpoint sees two attempts at that request for every fault. DBOS, Temporal, and Pi let batch A finish before injecting a fault on batch B. Their endpoint sees **A, B, B**, with batch A reused. All four runtimes complete the original logical run and render HTML.

| Runtime | Worker killed during a model request | HTTP 429 and lost response | Native evidence |
|---|---|---|---|
| LangGraph | Resume the original PostgreSQL thread and rerun the pending model call for the full report | The OpenAI client retries the full request within the same process | Final assistant response in the checkpoint and no pending node |
| Pydantic AI + DBOS | Launch against the same system database and wait on the original workflow | DBOS retries the model step | Workflow status SUCCESS and two recorded model steps |
| Pydantic AI + Temporal | Replace the worker and follow the existing workflow. The server times out and reassigns the activity | Temporal retries the activity | Workflow status COMPLETED. The activity for A settled on attempt 1 and the activity for B on attempt 2 |
| Pi Durable | Reopen the same SQLite store and resume the pending generation. Stable request IDs find the original submissions | The harness retries the generation | Two successful assistant turns. In the transport-failure runs, the B task also recorded an error turn |

The hosted search actions inside a Responses call are part of that call. The runtimes recovered at their own boundaries: the single checkpointed agent model call, DBOS step, Temporal activity, or Pi generation. If the endpoint finished a request but the worker never got the response, the worker issued the request again. The external request log shows this even when native history shows only the successful completion.

## Reproduce

From a fresh local Compose volume, start PostgreSQL and Temporal, then create the DBOS database once.

```sh
make setup
docker compose up -d --wait postgres temporal
docker compose exec -T postgres createdb -U weather weather_dbos
make recovery
```

Each demo prints the logical run ID, request attempts, and native status. For individual runs or manual recovery commands, see the [runtime READMEs](../README.md#runtimes). The fixture results measure recovery against a local endpoint. Live forecast quality and export to a real Logfire project require the provider credentials.
