#!/usr/bin/env bash
set -euo pipefail

source .venv/bin/activate

python paper_trader.py \
  --feed csv \
  --history-csv history.csv \
  --replay \
  --speed 600 \
  --loop \
  --ui rich
