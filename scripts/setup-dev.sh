#!/usr/bin/env bash
# Install deps and fix macOS editable-install breakage (UF_HIDDEN on .venv skips .pth).
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync "$@"
if [[ "$(uname)" == "Darwin" ]] && [[ -d .venv ]]; then
  chflags -R nohidden .venv 2>/dev/null || true
fi
