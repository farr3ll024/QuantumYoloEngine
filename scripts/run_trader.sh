#!/usr/bin/env bash
set -euo pipefail

# run the paper trader (defaults write to runtime/db + runtime/logs)
# usage:
#   ./scripts/run_trader.sh --feed demo --ui rich
#   ./scripts/run_trader.sh --feed csv --history-csv data/history.csv --replay --speed 1200 --loop

source .venv/bin/activate

python paper_trader.py "$@"