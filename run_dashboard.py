"""
run_dashboard.py — Dash entrypoint
Run: python run_dashboard.py [--port 8050] [--debug] [--host 127.0.0.1]
"""
from __future__ import annotations
import argparse, importlib, sys, types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


# ── Stub Streamlit BEFORE any dashboard.* module is imported.
#    dashboard/db.py decorates functions with @st.cache_data which segfaults
#    outside a Streamlit runtime on some platforms (macOS arm64 / Python 3.9).
def _noop_cache(func=None, **_kw):
    def decorator(f):
        f.clear = lambda: None
        return f

    return decorator(func) if func is not None else decorator


_st = types.ModuleType("streamlit")
_st.cache_data = _noop_cache
_st.cache_resource = _noop_cache
_st.session_state = {}
_st.secrets = {}
for _a in ("experimental_memo", "experimental_singleton", "write", "error",
           "warning", "info", "success", "stop"):
    setattr(_st, _a, lambda *a, **k: None)
sys.modules["streamlit"] = _st

# ── Now safe to import the Dash app ──
_mod = importlib.import_module("dashboard_dash.app")
create_app = _mod.create_app

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8050)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug)
