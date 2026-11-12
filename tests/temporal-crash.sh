#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

# 1. Resolve credentials once and reuse them in every Make command.
if [[ "${DURABLE_ENV_LOADED:-}" != "1" ]]; then
  exec ./scripts/1password.sh env DURABLE_ENV_LOADED=1 bash tests/temporal-crash.sh "$@"
fi

run_id="${1:-crash-$(date +%Y%m%d-%H%M%S)-$$}"
printf 'Run ID: %s\n' "$run_id"

# 2. Give background Make commands their own process groups, including children.
set -m
client_pid=""

# 3. Start the worker and register cleanup for exit, errors, and interrupts.
make temporal-worker </dev/null &
worker_pid=$!
cleanup() {
  if [[ -n "$worker_pid" ]]; then kill -KILL -- "-$worker_pid" 2>/dev/null || true; fi
  if [[ -n "$client_pid" ]]; then kill -KILL -- "-$client_pid" 2>/dev/null || true; fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# 4. Submit the workflow and wait for a native activity attempt to start.
make temporal-run RUN_ID="$run_id" </dev/null &
client_pid=$!
echo 'Waiting for a native model activity to start...'
until make --no-print-directory temporal-status RUN_ID="$run_id" STATUS_ARGS=--json |
  .venv/bin/python -c 'import json, sys; sys.exit(not json.load(sys.stdin).get("worker_started", False))'; do
  if ! kill -0 "$worker_pid" 2>/dev/null; then wait "$worker_pid"; exit 1; fi
  if ! kill -0 "$client_pid" 2>/dev/null; then wait "$client_pid"; exit 1; fi
  sleep 1
done

# 5. Choose the crash point, then kill the local worker and waiting client.
# Temporal stays running and retains the workflow history.
read -r -p "Press Enter to kill the worker (inspect Temporal UI or Logfire first)... "
if ! kill -0 "$client_pid" 2>/dev/null; then
  wait "$client_pid"
  echo 'The run already finished. Try again with a fresh run ID.' >&2
  exit 1
fi
cleanup
wait "$worker_pid" 2>/dev/null || true
wait "$client_pid" 2>/dev/null || true
client_pid=""
worker_pid=""

# 6. Inspect the saved activity history before resuming.
make temporal-status RUN_ID="$run_id"

# 7. Replace the worker and follow the same workflow ID.
# Unfinished activities can retry after the old attempt times out.
# The EXIT trap stops the replacement worker when the demo finishes.
read -r -p "Press Enter to start a replacement worker and resume... "
make temporal-worker </dev/null &
worker_pid=$!
make temporal-resume RUN_ID="$run_id"
