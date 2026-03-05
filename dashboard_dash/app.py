# dashboard_dash/app.py
from __future__ import annotations

import sys


# ── Neutralise Streamlit's @st.cache_data / @st.cache_resource before any
#    dashboard.* import touches them.  Outside a Streamlit runtime those
#    decorators trigger an internal segfault on some platforms (macOS arm64).
#    We replace them with a plain no-op decorator so the functions work fine.
def _noop_cache(func=None, **_kwargs):
    """Drop-in replacement for @st.cache_data / @st.cache_resource."""

    def decorator(f):
        # Attach a .clear() so call-sites like load_price_ticks.clear() don't crash
        f.clear = lambda: None
        return f

    if func is not None:
        # called as @st.cache_data  (no parentheses)
        return decorator(func)
    # called as @st.cache_data(ttl=...)
    return decorator


import types

_st_stub = types.ModuleType("streamlit")
_st_stub.cache_data = _noop_cache
_st_stub.cache_resource = _noop_cache
# Stub out everything else Streamlit that db.py / metrics.py might touch
for _attr in ("session_state", "secrets", "experimental_memo", "experimental_singleton"):
    setattr(_st_stub, _attr, {})
sys.modules.setdefault("streamlit", _st_stub)

import dash
from .components import CUSTOM_CSS, build_layout
from .callbacks import register_callbacks


def create_app() -> dash.Dash:
    app = dash.Dash(
        __name__,
        external_stylesheets=[],
        suppress_callback_exceptions=True,
        title="QYE",
        update_title=None,
    )

    DROPDOWN_FIX = """
    .sidebar .css-qc6sy-singleValue,
    .sidebar [class$="-singleValue"],
    .sidebar [class*="-singleValue"],
    .sidebar .Select-value-label,
    .sidebar .Select-value { color: #c9d1d9 !important; }
    .modebar-container { opacity: 0; transition: opacity 0.25s; background: transparent !important; }
    .js-plotly-plot:hover .modebar-container { opacity: 1; }
    """

    app.index_string = app.index_string.replace(
        "</head>",
        f"<style>{CUSTOM_CSS}</style><style>{DROPDOWN_FIX}</style></head>",
    )

    app.layout = build_layout()
    register_callbacks(app)
    return app
