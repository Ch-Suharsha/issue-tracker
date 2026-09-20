#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Load project .env so keys apply even when the shell has stale exports.
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

# If CLASSIFIER is not in .env, clear a stale `export CLASSIFIER=fake` from the shell.
if ! grep -qE '^[[:space:]]*CLASSIFIER=' .env 2>/dev/null; then
  unset CLASSIFIER || true
fi

if [[ "$(uname)" == Darwin ]] && [[ -d .venv ]]; then
  chflags -R nohidden .venv 2>/dev/null || true
fi
exec uv run issue-triage "$@"
