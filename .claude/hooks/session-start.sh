#!/bin/bash
# Installs dependencies when a Claude Code cloud session starts, so checks and
# tests run straight away. Does nothing on a local machine.
set -euo pipefail
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0
cd "$CLAUDE_PROJECT_DIR"

# Python reference engine: pip install only when the requirements files changed
# since the last install (hash kept in the git-ignored .cache/) or the test
# dependencies can't be imported.
marker=.cache/claude-requirements.sha256
want=$(cat requirements.txt requirements-dev.txt | sha256sum | cut -d' ' -f1)
if [ "$(cat "$marker" 2>/dev/null)" != "$want" ] \
  || ! python -c 'import pandas, yaml, pytest, hypothesis' 2>/dev/null; then
  # --ignore-installed: a Debian-packaged PyYAML in the cloud image cannot be
  # uninstalled by pip, so install alongside it (/usr/local wins on sys.path).
  python -m pip install -q --disable-pip-version-check --root-user-action=ignore --ignore-installed -r requirements-dev.txt
  mkdir -p .cache && echo "$want" > "$marker"
fi

# Web simulator: npm ci only when node_modules is missing or older than the lockfile.
cd web
if [ ! -f node_modules/.package-lock.json ] || [ package-lock.json -nt node_modules/.package-lock.json ]; then
  npm ci --no-audit --no-fund --loglevel=error
fi
