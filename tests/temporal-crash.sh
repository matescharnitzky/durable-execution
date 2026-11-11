#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
run_id="${1:-crash-$(date +%Y%m%d-%H%M%S)-$$}"
printf 'Run ID: %s\n' "$run_id"
set -m
client_pid=""
make temporal-worker </dev/null &
worker_pid=$!
cleanup() {
  kill -KILL -- "-$worker_pid" 2>/dev/null || true
  if [[ -n "$client_pid" ]]; then kill -KILL -- "-$client_pid" 2>/dev/null || true; fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
make temporal-run RUN_ID="$run_id" </dev/null &
client_pid=$!
echo 'Waiting for a native model activity to start...'
until make --no-print-directory temporal-status RUN_ID="$run_id" STATUS_ARGS=--json |
  .venv/bin/python -c 'import json, sys; sys.exit(not json.load(sys.stdin).get("worker_started", False))'; do
  if ! kill -0 "$worker_pid" 2>/dev/null; then wait "$worker_pid"; exit 1; fi
  if ! kill -0 "$client_pid" 2>/dev/null; then wait "$client_pid"; exit 1; fi
  sleep 1
done
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
make temporal-status RUN_ID="$run_id"
read -r -p "Press Enter to start a replacement worker and resume... "
make temporal-worker </dev/null &
worker_pid=$!
make temporal-resume RUN_ID="$run_id"
