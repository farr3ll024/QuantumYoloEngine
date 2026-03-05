# dashboard_dash/components.py
"""Layout + CSS. Zero Bootstrap. Single source of truth."""
from __future__ import annotations

from dash import dcc, html, dash_table

from dashboard.constants import (
    DEFAULT_RUNTIME_DB_PATH,
    DEFAULT_HISTORY_CSV_PATH, DEFAULT_STRATEGY_PATH,
)

AMBER = "#e8a020"
GREEN = "#26a65b"
RED = "#e03e52"
TEXT = "#b8c4cc"
SUB = "#546270"
BG = "#0a0c10"
SURF = "#0f1318"
RAISED = "#131b24"
BORDER = "#1c2330"
MONO = "'IBM Plex Mono','Menlo',monospace"

CUSTOM_CSS = '\n@import url(\'https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&display=swap\');\n\n/* ── reset ── */\n*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }\nhtml { font-size: 13px; }\nbody {\n  background: #0a0c10 !important;\n  color: #b8c4cc !important;\n  font-family: \'IBM Plex Mono\',\'Menlo\',monospace !important;\n  -webkit-font-smoothing: antialiased;\n}\n\n/* ── scrollbar ── */\n* { scrollbar-width: thin; scrollbar-color: #2a3340 transparent; }\n::-webkit-scrollbar { width: 4px; height: 4px; }\n::-webkit-scrollbar-thumb { background: #2a3340; border-radius: 2px; }\n\n/* ── dash chrome ── */\n._dash-loading, .dash-debug-menu, .dash-update-title { display: none !important; }\n\n/* ══════════════════════════════════════════════════════\n   NAVBAR\n══════════════════════════════════════════════════════ */\n.navbar {\n  height: 44px;\n  background: #0f1318;\n  border-bottom: 1px solid #1c2330;\n  display: flex; align-items: center;\n  justify-content: space-between;\n  padding: 0 20px;\n  position: sticky; top: 0; z-index: 200;\n  flex-shrink: 0;\n}\n.navbar-brand {\n  font-family: \'IBM Plex Mono\',\'Menlo\',monospace;\n  font-size: 0.72rem; font-weight: 600;\n  letter-spacing: 0.20em; text-transform: uppercase;\n  color: #e8a020;\n}\n.navbar-brand .dim { color: #546270; font-weight: 300; }\n.navbar-right { display: flex; align-items: center; gap: 16px; }\n.nav-pill {\n  font-size: 0.58rem; font-weight: 600;\n  letter-spacing: 0.1em; text-transform: uppercase;\n  padding: 2px 8px; border-radius: 2px;\n}\n.nav-pill-running {\n  color: #26a65b;\n  background: rgba(38,166,91,0.10);\n  border: 1px solid rgba(38,166,91,0.28);\n}\n.nav-pill-stopped {\n  color: #546270;\n  background: rgba(255,255,255,0.03);\n  border: 1px solid #1c2330;\n}\n.nav-tick { font-size: 0.62rem; color: #546270; }\n\n/* ══════════════════════════════════════════════════════\n   LAYOUT\n══════════════════════════════════════════════════════ */\n.body-wrap { display: flex; min-height: calc(100vh - 44px); }\n.main {\n  flex: 1; min-width: 0;\n  background: #0a0c10;\n  padding: 12px 16px;\n  overflow-y: auto;\n}\n\n/* ══════════════════════════════════════════════════════\n   SIDEBAR\n══════════════════════════════════════════════════════ */\n.sidebar {\n  width: 216px; min-width: 216px;\n  background: #0f1318;\n  border-right: 1px solid #1c2330;\n  padding: 8px 10px 28px;\n  overflow-y: auto; overflow-x: hidden;\n  flex-shrink: 0;\n}\n.sb-head {\n  font-size: 0.55rem; font-weight: 600;\n  color: #e8a020;\n  text-transform: uppercase; letter-spacing: 0.20em;\n  padding: 14px 2px 5px;\n  border-bottom: 1px solid rgba(232,160,32,0.14);\n  margin-bottom: 8px;\n}\n.sb-head:first-child { padding-top: 4px; }\n.sb-label {\n  font-size: 0.57rem; color: #546270;\n  text-transform: uppercase; letter-spacing: 0.10em;\n  margin: 8px 0 3px;\n}\n\n/* ── sidebar text inputs ── */\n.sidebar input[type=text],\n.sidebar input[type=number] {\n  width: 100% !important;\n  background: #0a0c10 !important;\n  border: 1px solid #1c2330 !important;\n  border-radius: 3px !important;\n  color: #b8c4cc !important;\n  font-family: \'IBM Plex Mono\',\'Menlo\',monospace !important;\n  font-size: 0.68rem !important;\n  padding: 4px 8px !important;\n  height: 26px !important;\n  outline: none !important;\n}\n.sidebar input[type=text]:focus,\n.sidebar input[type=number]:focus {\n  border-color: #e8a020 !important;\n  box-shadow: 0 0 0 2px rgba(232,160,32,0.14) !important;\n}\n\n/* ── dcc.Input wrapper ── */\n.sidebar .dash-input { display: block !important; }\n.sidebar .dash-input input {\n  width: 100% !important;\n  background: #0a0c10 !important;\n  border: 1px solid #1c2330 !important;\n  border-radius: 3px !important;\n  color: #b8c4cc !important;\n  font-family: \'IBM Plex Mono\',\'Menlo\',monospace !important;\n  font-size: 0.68rem !important;\n  padding: 4px 8px !important;\n  height: 26px !important;\n  outline: none !important;\n}\n\n/* ── SLIDERS — full replacement, kills purple ── */\n.rc-slider { margin: 8px 4px 16px; }\n.rc-slider-rail  { background: #1c2330 !important; height: 3px !important; border-radius: 2px !important; }\n.rc-slider-track { background: #e8a020  !important; height: 3px !important; border-radius: 2px !important; }\n.rc-slider-step  { background: transparent !important; }\n.rc-slider-dot   { display: none !important; }\n.rc-slider-handle {\n  width: 12px !important; height: 12px !important;\n  background: #0a0c10 !important;\n  border: 2px solid #e8a020 !important;\n  border-radius: 50% !important;\n  margin-top: -5px !important;\n  box-shadow: none !important;\n  opacity: 1 !important;\n  cursor: pointer !important;\n}\n.rc-slider-handle-dragging,\n.rc-slider-handle:hover {\n  border-color: #e8a020 !important;\n  box-shadow: 0 0 0 3px rgba(232,160,32,0.20) !important;\n}\n.rc-slider-tooltip-inner {\n  background: #131b24 !important;\n  border: 1px solid #1c2330 !important;\n  color: #b8c4cc !important;\n  font-family: \'IBM Plex Mono\',\'Menlo\',monospace !important;\n  font-size: 0.62rem !important;\n  padding: 2px 6px !important;\n  border-radius: 2px !important;\n  box-shadow: none !important;\n}\n.rc-slider-mark-text { color: #2a3340 !important; font-size: 0.57rem !important; }\n\n/* ── CHECKBOXES — fully custom ── */\ninput[type=checkbox] {\n  -webkit-appearance: none !important;\n  appearance: none !important;\n  width: 11px !important; height: 11px !important;\n  border: 1px solid #2a3340 !important;\n  border-radius: 2px !important;\n  background: #0a0c10 !important;\n  cursor: pointer !important;\n  flex-shrink: 0 !important;\n  vertical-align: middle !important;\n  margin-right: 5px !important;\n  margin-top: 1px !important;\n  position: relative !important;\n  display: inline-block !important;\n  transition: background .12s, border-color .12s !important;\n}\ninput[type=checkbox]:checked {\n  background: #e8a020 !important;\n  border-color: #e8a020 !important;\n}\ninput[type=checkbox]:checked::after {\n  content: \'\' !important;\n  display: block !important;\n  position: absolute !important;\n  left: 2px !important; top: 0px !important;\n  width: 4px !important; height: 7px !important;\n  border: 1.5px solid #0a0c10 !important;\n  border-top: none !important;\n  border-left: none !important;\n  transform: rotate(45deg) !important;\n}\n\n/* ── DROPDOWNS — cover both react-select v2 and v3 ── */\n.sidebar .dash-dropdown { margin-bottom: 4px; }\n\n/* react-select v2 (older dash) */\n.sidebar .Select-control {\n  background: #0a0c10 !important;\n  border: 1px solid #1c2330 !important;\n  border-radius: 3px !important;\n  min-height: 26px !important; height: 26px !important;\n  cursor: pointer !important;\n}\n.sidebar .Select-control:hover { border-color: #e8a020 !important; }\n.sidebar .Select.is-open .Select-control { border-color: #e8a020 !important; }\n.sidebar .Select-value,\n.sidebar .Select-value-label,\n.sidebar .Select-placeholder {\n  color: #b8c4cc !important;\n  font-family: \'IBM Plex Mono\',\'Menlo\',monospace !important;\n  font-size: 0.68rem !important;\n  line-height: 24px !important;\n  padding: 0 8px !important;\n}\n.sidebar .Select-placeholder { color: #546270 !important; }\n.sidebar .Select-arrow { border-top-color: #546270 !important; }\n.sidebar .Select-menu-outer {\n  background: #131b24 !important;\n  border: 1px solid #1c2330 !important;\n  border-radius: 3px !important;\n  z-index: 9999 !important;\n  box-shadow: 0 8px 24px rgba(0,0,0,0.6) !important;\n}\n.sidebar .Select-option {\n  background: transparent !important;\n  color: #b8c4cc !important;\n  font-family: \'IBM Plex Mono\',\'Menlo\',monospace !important;\n  font-size: 0.68rem !important;\n  padding: 5px 10px !important;\n  cursor: pointer !important;\n}\n.sidebar .Select-option.is-focused,\n.sidebar .Select-option:hover {\n  background: rgba(232,160,32,0.10) !important;\n  color: #e8a020 !important;\n}\n.sidebar .Select-option.is-selected {\n  background: rgba(232,160,32,0.16) !important;\n  color: #e8a020 !important;\n}\n\n/* react-select v3+ (newer dash) — attribute selectors survive minification */\n.sidebar [class$="-control"], .sidebar [class*="-control"] {\n  background: #0a0c10 !important;\n  border: 1px solid #1c2330 !important;\n  border-radius: 3px !important;\n  min-height: 26px !important;\n  box-shadow: none !important;\n  cursor: pointer !important;\n}\n.sidebar [class$="-control"]:hover, .sidebar [class*="-control"]:hover {\n  border-color: #e8a020 !important;\n}\n.sidebar [class*="singleValue"] {\n  color: #b8c4cc !important;\n  font-family: \'IBM Plex Mono\',\'Menlo\',monospace !important;\n  font-size: 0.68rem !important;\n}\n.sidebar [class*="placeholder"] {\n  color: #546270 !important;\n  font-family: \'IBM Plex Mono\',\'Menlo\',monospace !important;\n  font-size: 0.68rem !important;\n}\n.sidebar [class*="indicatorSeparator"] { display: none !important; }\n.sidebar [class*="dropdownIndicator"] svg {\n  fill: #546270 !important;\n  width: 12px !important; height: 12px !important;\n}\n.sidebar [class*="menu"] {\n  background: #131b24 !important;\n  border: 1px solid #1c2330 !important;\n  border-radius: 3px !important;\n  z-index: 9999 !important;\n  box-shadow: 0 8px 24px rgba(0,0,0,0.65) !important;\n}\n.sidebar [class*="option"] {\n  background: transparent !important;\n  color: #b8c4cc !important;\n  font-family: \'IBM Plex Mono\',\'Menlo\',monospace !important;\n  font-size: 0.68rem !important;\n  padding: 5px 10px !important;\n  cursor: pointer !important;\n}\n.sidebar [class*="option"]:hover,\n.sidebar [class*="option--is-focused"] {\n  background: rgba(232,160,32,0.10) !important;\n  color: #e8a020 !important;\n}\n.sidebar [class*="option--is-selected"] {\n  background: rgba(232,160,32,0.16) !important;\n  color: #e8a020 !important;\n}\n.sidebar [class*="ValueContainer"] {\n  padding: 0 8px !important;\n  min-height: 24px !important;\n}\n.sidebar [class*="Input"] input {\n  color: #b8c4cc !important;\n  font-family: \'IBM Plex Mono\',\'Menlo\',monospace !important;\n  font-size: 0.68rem !important;\n}\n\n/* ── sidebar buttons ── */\n.engine-running { color: #26a65b; font-size: 0.68rem; font-weight: 600; }\n.engine-stopped { color: #546270;   font-size: 0.68rem; }\n\n/* ══════════════════════════════════════════════════════\n   TABS\n══════════════════════════════════════════════════════ */\n.custom-tabs .tab {\n  font-family: \'IBM Plex Mono\',\'Menlo\',monospace !important;\n  font-size: 0.60rem !important; font-weight: 500 !important;\n  text-transform: uppercase !important; letter-spacing: 0.12em !important;\n  padding: 10px 16px !important;\n  border: none !important;\n  border-bottom: 2px solid transparent !important;\n  background: transparent !important;\n  color: #546270 !important;\n  cursor: pointer; white-space: nowrap;\n  transition: color .15s, border-color .15s;\n}\n.custom-tabs .tab:hover { color: #b8c4cc !important; }\n.custom-tabs .tab--selected {\n  color: #e8a020 !important;\n  border-bottom: 2px solid #e8a020 !important;\n}\n.custom-tabs .tab-container {\n  border-bottom: 1px solid #1c2330 !important;\n  background: transparent !important;\n}\n.custom-tabs .tab-content { padding-top: 2px !important; }\n\n/* ══════════════════════════════════════════════════════\n   CARDS\n══════════════════════════════════════════════════════ */\n.card {\n  background: #0f1318;\n  border: 1px solid #1c2330;\n  border-top: 1px solid rgba(232,160,32,0.20);\n  border-radius: 4px;\n  padding: 10px 13px;\n  margin-bottom: 10px;\n}\n.card-title {\n  font-size: 0.55rem; font-weight: 600;\n  color: #546270; text-transform: uppercase;\n  letter-spacing: 0.14em; margin-bottom: 9px;\n}\n\n/* ══════════════════════════════════════════════════════\n   STAT RAIL\n══════════════════════════════════════════════════════ */\n.stat-row {\n  display: flex; flex-direction: row;\n  border: 1px solid #1c2330;\n  border-top: 1px solid rgba(232,160,32,0.20);\n  border-radius: 4px; overflow: hidden;\n  margin-bottom: 10px;\n}\n.stat-tile {\n  flex: 1; padding: 12px 16px;\n  background: #0f1318;\n  border-right: 1px solid #1c2330;\n}\n.stat-tile:last-child { border-right: none; }\n.stat-label {\n  font-size: 0.54rem; font-weight: 500; color: #546270;\n  text-transform: uppercase; letter-spacing: 0.12em;\n  margin-bottom: 6px;\n}\n.stat-value {\n  font-family: \'IBM Plex Mono\',\'Menlo\',monospace;\n  font-size: 1.05rem; font-weight: 600;\n  color: #b8c4cc; letter-spacing: -0.02em; line-height: 1;\n}\n.stat-value.pos   { color: #26a65b; }\n.stat-value.neg   { color: #e03e52;   }\n.stat-value.amber { color: #e8a020; }\n.stat-value.muted { color: #546270;   }\n\n/* ══════════════════════════════════════════════════════\n   PLOTLY modebar\n══════════════════════════════════════════════════════ */\n.modebar-container {\n  opacity: 0 !important;\n  transition: opacity 0.2s !important;\n  background: transparent !important;\n}\n.js-plotly-plot:hover .modebar-container { opacity: 1 !important; }\n.modebar-btn svg {\n  width: 14px !important; height: 14px !important;\n  fill: #546270 !important;\n}\n.modebar-btn:hover svg { fill: #e8a020 !important; }\n.modebar-group { background: transparent !important; }\n\n/* ══════════════════════════════════════════════════════\n   DATA TABLES\n══════════════════════════════════════════════════════ */\n.dash-table-container {\n  border: 1px solid #1c2330 !important;\n  border-radius: 3px !important; overflow: hidden !important;\n}\n.dash-spreadsheet-inner table {\n  border-collapse: collapse !important; width: 100% !important;\n}\n.dash-spreadsheet-inner th {\n  background: #131b24 !important; color: #546270 !important;\n  font-family: \'IBM Plex Mono\',\'Menlo\',monospace !important; font-size: 0.57rem !important;\n  font-weight: 600 !important; text-transform: uppercase !important;\n  letter-spacing: 0.10em !important; border: none !important;\n  border-bottom: 1px solid #1c2330 !important;\n  padding: 6px 10px !important; white-space: nowrap !important;\n}\n.dash-spreadsheet-inner td {\n  background: transparent !important; color: #b8c4cc !important;\n  font-family: \'IBM Plex Mono\',\'Menlo\',monospace !important; font-size: 0.70rem !important;\n  border: none !important;\n  border-bottom: 1px solid rgba(255,255,255,0.025) !important;\n  padding: 5px 10px !important; white-space: nowrap !important;\n}\n.dash-spreadsheet-inner tr:hover td {\n  background: rgba(232,160,32,0.04) !important;\n}\n.dash-filter input {\n  background: #0a0c10 !important; color: #b8c4cc !important;\n  font-family: \'IBM Plex Mono\',\'Menlo\',monospace !important; font-size: 0.65rem !important;\n  border: none !important;\n  border-bottom: 1px solid #1c2330 !important;\n  outline: none !important; padding: 3px 10px !important;\n}\n\n/* ══════════════════════════════════════════════════════\n   BUTTONS\n══════════════════════════════════════════════════════ */\nbutton, .btn {\n  font-family: \'IBM Plex Mono\',\'Menlo\',monospace !important;\n  font-size: 0.60rem !important; font-weight: 600 !important;\n  letter-spacing: 0.07em !important; text-transform: uppercase !important;\n  border-radius: 3px !important; padding: 5px 12px !important;\n  cursor: pointer !important; transition: opacity .15s !important;\n  outline: none !important;\n}\nbutton:hover, .btn:hover { opacity: 0.78 !important; }\n.btn-amber {\n  background: #e8a020 !important; color: #060400 !important;\n  border: none !important; font-weight: 700 !important;\n}\n.btn-ghost {\n  background: transparent !important; color: #e8a020 !important;\n  border: 1px solid rgba(232,160,32,0.32) !important;\n}\n.btn-ghost:hover { background: rgba(232,160,32,0.08) !important; }\n.btn-danger {\n  background: #e03e52 !important; color: #fff !important;\n  border: none !important;\n}\n.btn-sm { padding: 4px 10px !important; font-size: 0.58rem !important; }\n.w-100 { width: 100% !important; }\n.mt-1 { margin-top: 6px !important; }\n\n/* ══════════════════════════════════════════════════════\n   ALERTS\n══════════════════════════════════════════════════════ */\n.alert {\n  font-family: \'IBM Plex Mono\',\'Menlo\',monospace; font-size: 0.67rem;\n  padding: 6px 10px; border-radius: 3px;\n  border-left: 3px solid; margin-top: 6px;\n  border-top: none; border-right: none; border-bottom: none;\n}\n.alert-success   { background: rgba(38,166,91,0.08);  border-color: #26a65b; color: #26a65b; }\n.alert-danger    { background: rgba(224,62,82,0.08);  border-color: #e03e52;   color: #e03e52;   }\n.alert-warning   { background: rgba(232,160,32,0.08); border-color: #e8a020; color: #e8a020; }\n.alert-secondary { background: rgba(255,255,255,0.03);border-color: #2a3340;   color: #546270;   }\n.alert-info      { background: rgba(74,143,232,0.08); border-color: #4a8fe8;  color: #4a8fe8;  }\n\n/* ══════════════════════════════════════════════════════\n   TEXTAREA / PRE\n══════════════════════════════════════════════════════ */\ntextarea {\n  width: 100% !important; background: #0a0c10 !important;\n  border: 1px solid #1c2330 !important; border-radius: 3px !important;\n  color: #b8c4cc !important; font-family: \'IBM Plex Mono\',\'Menlo\',monospace !important;\n  font-size: 0.70rem !important; padding: 8px !important;\n  resize: vertical !important; outline: none !important;\n}\ntextarea:focus {\n  border-color: #e8a020 !important;\n  box-shadow: 0 0 0 2px rgba(232,160,32,0.12) !important;\n}\npre, code {\n  background: #0a0c10 !important; border: 1px solid #1c2330 !important;\n  border-radius: 3px !important; color: #b8c4cc !important;\n  font-family: \'IBM Plex Mono\',\'Menlo\',monospace !important; font-size: 0.65rem !important;\n  padding: 8px 10px !important; white-space: pre-wrap !important;\n}\n\n/* ══════════════════════════════════════════════════════\n   FLEX GRID\n══════════════════════════════════════════════════════ */\n.row2 { display: flex; gap: 10px; margin-bottom: 10px; }\n.row2 > * { flex: 1; min-width: 0; }\n.col-8 { flex: 8 !important; } .col-4 { flex: 4 !important; }\n.col-6 { flex: 6 !important; } .col-3 { flex: 3 !important; }\n.col-2 { flex: 2 !important; } .col-1 { flex: 1 !important; }\n'


def _label(t): return html.Div(t, className="sb-label")


def _head(t):  return html.Div(t, className="sb-head")


def _card_title(t): return html.Div(t, className="card-title")


INPUT_STYLE = dict(
    width="100%", background=BG,
    border=f"1px solid {BORDER}", borderRadius="3px",
    color=TEXT, fontFamily=MONO, fontSize="0.68rem",
    padding="4px 8px", height="26px", outline="none",
)


def _inp(id_, val, **kw):
    return dcc.Input(id=id_, type="text", value=val, debounce=True,
                     style=INPUT_STYLE, **kw)


def _dd(id_, opts, val=None, **kw):
    v = val if val is not None else (opts[0]["value"] if opts and isinstance(opts[0], dict) else opts[0])
    return dcc.Dropdown(id=id_, options=opts, value=v, clearable=False,
                        style={"fontSize": "0.68rem", "marginBottom": "3px"}, **kw)


def _slider(id_, mn, mx, step, val, marks=None):
    return dcc.Slider(id=id_, min=mn, max=mx, step=step, value=val,
                      marks=marks or {},
                      tooltip={"placement": "bottom", "always_visible": False})


def _graph(id_, h=340):
    return dcc.Graph(id=id_,
                     config={"displayModeBar": "hover", "scrollZoom": True, "responsive": True,
                             "displaylogo": False,
                             "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"]},
                     style={"height": f"{h}px"})


def _table(id_, h="400px"):
    return dash_table.DataTable(
        id=id_,
        style_table={"overflowX": "auto", "maxHeight": h, "overflowY": "auto"},
        fixed_rows={"headers": True},
        page_size=100, sort_action="native", filter_action="native",
        style_header={
            "background": RAISED, "color": SUB, "fontFamily": MONO,
            "fontSize": "10px", "fontWeight": "600", "textTransform": "uppercase",
            "letterSpacing": "0.10em", "border": "none",
            "borderBottom": f"1px solid {BORDER}", "padding": "6px 10px",
        },
        style_cell={
            "background": "transparent", "color": TEXT, "fontFamily": MONO,
            "fontSize": "11px", "border": "none",
            "borderBottom": "1px solid rgba(255,255,255,0.025)", "padding": "5px 10px",
        },
        style_data_conditional=[
            {"if": {"state": "active"}, "background": "rgba(232,160,32,0.05)", "border": "none"},
        ],
        style_filter={
            "background": BG, "color": TEXT, "fontFamily": MONO, "fontSize": "11px",
            "border": "none", "borderBottom": f"1px solid {BORDER}",
        },
    )


def sidebar():
    return html.Div(className="sidebar", children=[
        _head("Database"),
        _label("SQLite path"),
        _inp("db-path", DEFAULT_RUNTIME_DB_PATH),

        _head("Engine"),
        html.Div(id="engine-status-text", className="engine-stopped", children="● stopped"),
        html.Div(id="engine-pid-text",
                 style={"fontSize": "0.60rem", "color": SUB, "marginBottom": "6px", "wordBreak": "break-all"}),
        _label("Run mode"),
        _dd("engine-mode", [
            {"label": "CSV Replay", "value": "csv"},
            {"label": "Demo rich", "value": "demo_rich"},
            {"label": "Demo console", "value": "demo_console"},
        ]),
        _label("Replay speed"),
        _dd("replay-speed",
            [{"label": f"{v}×", "value": v} for v in [1, 10, 60, 120, 300, 600, 1200, 3600, 7200, 14400]], val=3600),
        _label("History CSV"),
        _inp("history-csv-path", DEFAULT_HISTORY_CSV_PATH),
        html.Div(id="engine-est-runtime",
                 style={"fontSize": "0.60rem", "color": SUB, "margin": "4px 0"}),
        html.Div(id="engine-cmd-preview",
                 style={"fontSize": "0.55rem", "color": "#2a3340", "wordBreak": "break-all", "marginBottom": "8px",
                        "lineHeight": "1.5"}),
        html.Div(style={"display": "flex", "gap": "6px"}, children=[
            html.Button("▶ Start", id="btn-start-engine", n_clicks=0, className="btn btn-amber btn-sm"),
            html.Button("■ Stop", id="btn-stop-engine", n_clicks=0, className="btn btn-ghost btn-sm"),
        ]),
        html.Div(id="engine-action-msg"),

        _head("Strategy"),
        _label("YAML path"),
        _inp("strategy-path", DEFAULT_STRATEGY_PATH),

        _head("Display"),
        _label("Refresh (s)"),
        _slider("refresh-sec", 1, 15, 1, 3, {1: "1", 5: "5", 15: "15"}),
        _label("Asset focus"),
        _dd("asset-focus", [{"label": "All", "value": "all"}, {"label": "BTC-USD", "value": "BTC-USD"},
                            {"label": "ETH-USD", "value": "ETH-USD"}]),
        _label("Chart type"),
        _dd("chart-type", [{"label": "Line", "value": "line"}, {"label": "Candlestick", "value": "candlestick"}]),
        _label("Candle interval"),
        _dd("candle-interval", [{"label": v, "value": v} for v in ["1m", "5m", "15m", "1h", "4h", "1d"]], val="5m"),
        _label("Window (ticks)"),
        _slider("last-n-ticks", 50, 2000, 50, 500, {50: "50", 1000: "1k", 2000: "2k"}),
        html.Div(style={"marginTop": "8px"}, children=[
            dcc.Checklist(id="display-options",
                          options=[{"label": " Trade overlays", "value": "overlays"},
                                   {"label": " Signals only", "value": "signals_only"},
                                   {"label": " Show orders", "value": "show_orders"}],
                          value=["overlays", "signals_only", "show_orders"],
                          inputStyle={"marginRight": "5px"},
                          labelStyle={"display": "block", "margin": "3px 0", "fontSize": "0.65rem", "color": SUB,
                                      "cursor": "pointer"},
                          ),
        ]),

        _head("Filters"),
        _label("Levels"),
        dcc.Checklist(id="event-levels",
                      options=[{"label": f" {l}", "value": l} for l in ["info", "warn", "error"]],
                      value=["info", "warn"],
                      inputStyle={"marginRight": "4px"},
                      labelStyle={"display": "inline-block", "marginRight": "8px", "fontSize": "0.65rem", "color": SUB,
                                  "cursor": "pointer"},
                      ),
        _label("Search"),
        _inp("event-search", "", placeholder="filter…"),
        _label("Max events"),
        _slider("event-limit", 50, 2000, 50, 500, {50: "50", 1000: "1k", 2000: "2k"}),

        _head("Developer"),
        html.Button("Clear All Data", id="btn-clear-data", n_clicks=0, className="btn btn-danger btn-sm w-100"),
        html.Button("Confirm Clear", id="btn-confirm-clear", n_clicks=0, className="btn btn-danger btn-sm w-100 mt-1",
                    style={"display": "none"}),
        html.Div(id="clear-data-msg"),
        html.Div(style={"height": "20px"}),
    ])


def tab_overview():
    return html.Div([
        html.Div(id="status-rail"),
        html.Div(className="row2", children=[
            html.Div(className="col-8", children=[
                html.Div(className="card", children=[_card_title("Price"), _graph("price-chart", 320)]),
                html.Div(className="card", children=[_card_title("Equity"), _graph("equity-chart", 170)]),
            ]),
            html.Div(className="col-4", children=[
                html.Div(className="card", style={"height": "calc(100% - 10px)"},
                         children=[_card_title("Positions"), _table("positions-table", "490px")]),
            ]),
        ]),
    ])


def tab_orders():
    return html.Div([html.Div(className="card", children=[_card_title("Orders"), _table("orders-table")])])


def tab_events():
    return html.Div([html.Div(className="card", children=[_card_title("Events"), _table("events-table")])])


def tab_history():
    return html.Div([
        html.Div(className="card", children=[_card_title("History File"), html.Div(id="history-summary")]),
        html.Div(className="card", children=[
            _card_title("Regenerate"),
            html.Div(className="row2", style={"alignItems": "flex-end", "flexWrap": "wrap"}, children=[
                html.Div(className="col-4", children=[_label("Days back"),
                                                      _slider("hist-days", 3, 365, 1, 183,
                                                              {3: "3", 183: "183", 365: "365"})]),
                html.Div(className="col-2", children=[_label("Granularity"),
                                                      _dd("hist-granularity", [{"label": "Hourly", "value": "hourly"},
                                                                               {"label": "Daily", "value": "daily"}])]),
                html.Div(className="col-2", children=[_label("Provider"),
                                                      _dd("hist-provider", [{"label": "Binance", "value": "binance"},
                                                                            {"label": "CoinGecko",
                                                                             "value": "coingecko"}])]),
                html.Div(className="col-3",
                         children=[_label("Output path"), _inp("hist-out-path", DEFAULT_HISTORY_CSV_PATH)]),
                html.Div(style={"display": "flex", "alignItems": "flex-end"}, children=[
                    html.Button("Run", id="btn-gen-history", n_clicks=0, className="btn btn-amber btn-sm")]),
            ]),
            html.Div(id="hist-gen-output", style={"marginTop": "12px"}),
        ]),
    ])


def tab_strategy():
    return html.Div([
        html.Div(className="card", children=[html.Div(id="strategy-summary")]),
        html.Div(className="card", children=[
            _card_title("Edit Strategy YAML"),
            dcc.Textarea(id="strategy-editor", rows=22,
                         style={"width": "100%", "background": BG, "border": f"1px solid {BORDER}",
                                "borderRadius": "3px", "color": TEXT, "fontFamily": MONO,
                                "fontSize": "0.70rem", "padding": "8px", "resize": "vertical", "outline": "none"}),
            html.Div(style={"display": "flex", "gap": "8px", "marginTop": "10px"}, children=[
                html.Button("Validate", id="btn-validate-strategy", n_clicks=0, className="btn btn-ghost btn-sm"),
                html.Button("Save Strategy", id="btn-save-strategy", n_clicks=0, className="btn btn-amber btn-sm"),
            ]),
            html.Div(id="strategy-action-msg"),
        ]),
    ])


def tab_reports():
    return html.Div([
        html.Div(id="reports-kpi-row"),
        html.Div(className="card", children=[
            html.Div(style={"display": "flex", "justifyContent": "space-between", "alignItems": "flex-start"},
                     children=[
                         html.Div(id="reports-config-display"),
                         html.Div(style={"display": "flex", "flexDirection": "column", "alignItems": "flex-end",
                                         "gap": "8px"}, children=[
                             dcc.Checklist(id="reports-save-snapshot",
                                           options=[{"label": " Save snapshot", "value": "save"}], value=["save"],
                                           inputStyle={"marginRight": "5px"},
                                           labelStyle={"fontSize": "0.65rem", "color": SUB}),
                             html.Button("Build Report", id="btn-build-report", n_clicks=0,
                                         className="btn btn-amber btn-sm"),
                         ]),
                     ]),
            html.Div(id="reports-build-msg"),
        ]),
        dcc.Tabs(id="report-tabs", className="custom-tabs", value="r-summary", children=[
            dcc.Tab(label="Summary", value="r-summary",
                    children=html.Div(id="report-summary-content", style={"paddingTop": "10px"})),
            dcc.Tab(label="Trades", value="r-trades",
                    children=html.Div(id="report-trades-content", style={"paddingTop": "10px"})),
            dcc.Tab(label="Equity", value="r-equity",
                    children=html.Div(id="report-equity-content", style={"paddingTop": "10px"})),
            dcc.Tab(label="Events", value="r-events",
                    children=html.Div(id="report-events-content", style={"paddingTop": "10px"})),
            dcc.Tab(label="Exports", value="r-exports",
                    children=html.Div(id="report-exports-content", style={"paddingTop": "10px"})),
            dcc.Tab(label="Compare", value="r-compare",
                    children=html.Div(id="report-compare-content", style={"paddingTop": "10px"})),
        ]),
    ])


def tab_diagnostics():
    return html.Div(
        [html.Div(className="card", children=[_card_title("Diagnostics"), html.Div(id="diagnostics-content")])])


def build_layout():
    return html.Div([
        dcc.Interval(id="main-interval", interval=3000, n_intervals=0),
        dcc.Store(id="store-report-bundle"),
        dcc.Store(id="store-confirm-clear", data=False),
        dcc.Download(id="download-zip"),

        html.Div(className="navbar", children=[
            html.Div(className="navbar-brand", children=[
                "QUANTUM", html.Span(" YOLO ", "dim"), "ENGINE",
            ]),
            html.Div(className="navbar-right", children=[
                html.Div(id="engine-navbar-pill"),
                html.Div(id="navbar-tick-age", className="nav-tick"),
            ]),
        ]),

        html.Div(className="body-wrap", children=[
            sidebar(),
            html.Div(className="main", children=[
                dcc.Tabs(id="main-tabs", className="custom-tabs", value="tab-overview", children=[
                    dcc.Tab(label="Overview", value="tab-overview", children=tab_overview()),
                    dcc.Tab(label="Orders", value="tab-orders", children=tab_orders()),
                    dcc.Tab(label="Events", value="tab-events", children=tab_events()),
                    dcc.Tab(label="History", value="tab-history", children=tab_history()),
                    dcc.Tab(label="Strategy", value="tab-strategy", children=tab_strategy()),
                    dcc.Tab(label="Reports", value="tab-reports", children=tab_reports()),
                    dcc.Tab(label="Diagnostics", value="tab-diagnostics", children=tab_diagnostics()),
                ]),
            ]),
        ]),
    ])
