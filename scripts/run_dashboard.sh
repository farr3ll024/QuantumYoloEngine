#!/usr/bin/env bash
set -euo pipefail

# run the streamlit dashboard (defaults to runtime/db/paper_trader.db)
# usage:
#   ./scripts/run_dashboard.sh
#   ./scripts/run_dashboard.sh --server.port 8502

source .venv/bin/activate

python -m streamlit run dashboard_streamlit.py "$@"