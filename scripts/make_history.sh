#!/usr/bin/env bash
set -euo pipefail

# generate historical csv for replay
# default output: data/history.csv
#
# usage:
#   ./scripts/make_history.sh
#   ./scripts/make_history.sh --provider coingecko --granularity hourly --out data/history.csv

source .venv/bin/activate

python make_history_6mo.py --provider binance --granularity hourly --out data/history.csv "$@"