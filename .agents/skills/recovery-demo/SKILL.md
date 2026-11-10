---
name: recovery-demo
description: Run and document the lab's durable execution recovery scenarios.
---

# Recovery demo

Use the runtime's README for setup and commands. Keep the durable store and original run ID across worker replacement. Use the credential-free fake OpenAI endpoint for repeatable fault injection.

1. Let batch A finish and block batch B at the endpoint. Kill the worker and recover the original run. Check whether A was reused and B retried.
2. Return HTTP 429 once. Identify which layer handled the retry and whether it needed a restart.
3. Finish a request at the endpoint and close the connection before delivering the response. Check for a duplicate request.

Use the endpoint request log as evidence only. Compare it with native runtime history and check whether the report finished. If Logfire is configured, correlate observable events across restart using the logical run ID. Record the commands, outcomes, and gaps. Keep secrets and raw model payloads out of shared evidence.
