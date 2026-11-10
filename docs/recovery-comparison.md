# Recovery comparison

The fixture uses two one-city batches. It lets A return, then injects a failure on B. All four runtimes completed the original logical run and rendered HTML in each scenario. The endpoint saw **A, B, B** in all 12 runs. No runtime needed to search for A again. The second B was a new HTTP request.

| Runtime | Worker killed during B | HTTP 429 and lost response | Native evidence |
|---|---|---|---|
| LangGraph | Reinvoke with no new input and the original PostgreSQL thread ID | LangChain’s model retry middleware retries B | Two completed batches and no next node in the final checkpoint |
| Pydantic AI + DBOS | Launch against the same system database and wait on the original workflow | DBOS retries the model step | Workflow status SUCCESS and two recorded model steps |
| Pydantic AI + Temporal | Replace the worker and follow the existing workflow. The server times out and reassigns the activity | Temporal retries the activity | Workflow status COMPLETED. The activity for A settled on attempt 1 and the activity for B on attempt 2 |
| Pi Durable | Reopen the same SQLite store and resume the pending generation. Stable request IDs find the original submissions | The harness retries the generation | Two successful assistant turns. In the transport-failure runs, the B task also recorded an error turn |

The hosted search actions inside a Responses call are part of that call. The runtimes recovered at their own boundaries: the checkpointed agent model turn, DBOS step, Temporal activity, or Pi generation. If the endpoint finished a request but the worker never got the response, the worker issued the request again. The external request log shows this even when native history shows only the successful completion.

## Reproduce

From a fresh local Compose volume, start PostgreSQL and Temporal, then create the DBOS database once.

```sh
make setup
docker compose up -d --wait postgres temporal
docker compose exec -T postgres createdb -U weather weather_dbos
make recovery
```

Each demo prints the logical run ID, request attempts, and native status. For individual runs or manual recovery commands, see the [runtime READMEs](../README.md#runtimes). The fixture results measure recovery against a local endpoint. Live forecast quality and export to a real Logfire project require the provider credentials.
