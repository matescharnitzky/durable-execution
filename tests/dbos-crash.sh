#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

if [[ "${DURABLE_ENV_LOADED:-}" != "1" ]]; then
  exec ./scripts/1password.sh env DURABLE_ENV_LOADED=1 bash tests/dbos-crash.sh "$@"
fi

run_id="${1:-crash-$(date +%Y%m%d-%H%M%S)-$$}"
printf 'Run ID: %s\n' "$run_id"

# Job control gives Make and its worker children their own process group.
set -m
make dbos-run RUN_ID="$run_id" </dev/null &
worker_pid=$!
trap 'kill -KILL -- "-$worker_pid" 2>/dev/null || true' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

echo 'Waiting for the workflow to be stored...'
until make --no-print-directory dbos-status RUN_ID="$run_id" STATUS_ARGS=--json |
  .venv/bin/python -c 'import json, sys; sys.exit(json.load(sys.stdin)["state"] == "unknown")'; do
  if ! kill -0 "$worker_pid" 2>/dev/null; then
    wait "$worker_pid"
    echo 'The worker exited before storing the workflow.' >&2
    exit 1
  fi
  sleep 1
done

echo 'Workflow stored. The run can now be resumed after a crash.'
read -r -p "Press Enter to kill the worker (inspect Logfire or pgAdmin first)... "
if ! kill -0 "$worker_pid" 2>/dev/null; then
  wait "$worker_pid"
  echo 'The run already finished. Try again with a fresh run ID.' >&2
  exit 1
fi

kill -KILL -- "-$worker_pid"
wait "$worker_pid" 2>/dev/null || true
trap - EXIT

make dbos-status RUN_ID="$run_id"
read -r -p "Press Enter to resume the same run... "
make dbos-resume RUN_ID="$run_id"
