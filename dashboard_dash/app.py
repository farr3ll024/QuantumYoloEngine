# dashboard_dash/app.py
from __future__ import annotations

import sys


def _noop_cache(func=None, **_kwargs):
    def decorator(f):
        f.clear = lambda: None
        return f
    if func is not None:
        return decorator(func)
    return decorator


import types

_st_stub = types.ModuleType("streamlit")
_st_stub.cache_data = _noop_cache
_st_stub.cache_resource = _noop_cache
for _attr in ("session_state", "secrets", "experimental_memo", "experimental_singleton"):
    setattr(_st_stub, _attr, {})
sys.modules.setdefault("streamlit", _st_stub)

import dash
from .components import CUSTOM_CSS, DROPDOWN_CSS, build_layout
from .callbacks import register_callbacks


def create_app() -> dash.Dash:
    app = dash.Dash(
        __name__,
        external_stylesheets=[],
        suppress_callback_exceptions=True,
        title="QYE",
        update_title=None,
    )

    # Main theme CSS injected into <head>
    app.index_string = app.index_string.replace(
        "</head>",
        f"<style>{CUSTOM_CSS}</style></head>",
    )

    # Dropdown override injected right before </body> — loads AFTER react-select's
    # own stylesheet so our rules win without fighting specificity.
    app.index_string = app.index_string.replace(
        "</body>",
        f"<style>{DROPDOWN_CSS}</style></body>",
    )

    app.layout = build_layout()
    register_callbacks(app)
    return app