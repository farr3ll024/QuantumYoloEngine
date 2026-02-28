#!/usr/bin/env bash
set -euo pipefail

source .venv/bin/activate

python make_history_6mo.py \
  --provider binance \
  --binance-base-url https://data-api.binance.vision \
  --granularity hourly \
  --out history.csv
