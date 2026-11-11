#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

if [[ $# -eq 0 ]]; then
  echo 'Usage: scripts/1password.sh command [args...]' >&2
  exit 2
fi

# Ordinary .env files and exported variables work without 1Password.
if [[ "${COMPOSE_DISABLE_ENV_FILE:-}" != "1" && -f .env ]] &&
  grep -Eq '^[[:space:]]*(export[[:space:]]+)?[A-Za-z_][A-Za-z0-9_]*[[:space:]]*=.*op://' .env; then
  exec op run --env-file .env --no-masking -- "$@"
fi

exec "$@"
