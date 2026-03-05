# dashboard_dash/callbacks.py
"""
All Dash callbacks.

Design principle: dcc.Interval fires every N seconds and updates ONLY the
Output components it's wired to. The browser never does a page navigation or
full reload — only the specific DOM nodes change. Scroll position is preserved
by the browser automatically.
"""
from __future__ import annotations

import io
from typing import Optional

import pandas as pd
import yaml
from dash import Input, Output, State, dash_table, dcc, html, no_update

from dashboard.constants import DEFAULT_HISTORY_CSV_PATH
from dashboard.db import load_events, load_orders, load_positions, load_price_ticks, clear_all_data
from dashboard.engine_control import get_status as get_engine_status, start_engine, stop_engine
from dashboard.history_manager import regenerate_history
from dashboard.metrics import build_unrealized_pnl, compute_asset_pnl_rows, last_db_tick_ts, load_equity_curve
from dashboard.strategy_manager import load_strategy_yaml, save_strategy_yaml, validate_strategy_dict
from dashboard.ui_parts.data import apply_asset_focus, apply_events_filters

_C = {"green": "#2dce89", "red": "#f5365c", "amber": "#f5a623", "sub": "#8b949e", "text": "#cdd9e5"}

from .charts import (
    PLOTLY_CONFIG, add_trade_overlays, equity_compare_fig, equity_fig,
    event_bar_fig, price_candle_fig, price_line_fig, trades_bar_fig,
)

# bring in report helpers from the existing streamlit module (pure python, no st calls)
from dashboard.ui_parts.render_reports import (
    _build_report_bundle, _build_zip_bundle, _list_saved_reports,
    _load_saved_report, _build_kpi_compare_table, _save_report_snapshot, _summary_value,
)


# ── small helpers ────────────────────────────────────────────────────────────

def _fmt_money(v) -> str:
    if v is None:
        return "—"
    try:
        return f"${float(v):,.2f}"
    except Exception:
        return "—"


def _fmt_pct(v) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v) * 100:.1f}%"
    except Exception:
        return "—"


def _pnl_color(v: float) -> str:
    try:
        if float(v) > 0: return _C["green"]
        if float(v) < 0: return _C["red"]
    except Exception:
        pass
    return _C["sub"]


def _stat(label: str, value: str, color: Optional[str] = None) -> html.Div:
    # Map hex colors to CSS class names for the stat-value
    _cls_map = {
        _C["green"]: "stat-value pos",
        _C["red"]: "stat-value neg",
        _C["amber"]: "stat-value amber",
        _C["sub"]: "stat-value muted",
    }
    cls = _cls_map.get(color, "stat-value")
    return html.Div(className="stat-tile", children=[
        html.Div(label, className="stat-label"),
        html.Div(value, className=cls),
    ])


def _df_to_records(df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    """Returns (data, columns) for DataTable."""
    if df.empty:
        return [], []
    df = df.copy()
    for col in df.select_dtypes(include=["datetime64[ns, UTC]", "datetime64[ns]"]).columns:
        df[col] = df[col].astype(str)
    data = df.to_dict("records")
    columns = [{"name": c, "id": c} for c in df.columns]
    return data, columns


def _alert(msg: str, color: str = "success") -> html.Div:
    return html.Div(msg, className=f"alert alert-{color}")


def _get_opts(display_options: list) -> tuple[bool, bool, bool]:
    overlays = "overlays" in (display_options or [])
    signals_only = "signals_only" in (display_options or [])
    show_orders = "show_orders" in (display_options or [])
    return overlays, signals_only, show_orders


# ── interval: sync interval control ─────────────────────────────────────────

def register_callbacks(app):
    @app.callback(
        Output("main-interval", "interval"),
        Input("refresh-sec", "value"),
    )
    def sync_interval(refresh_sec):
        return max(1, int(refresh_sec or 3)) * 1000

    # ── navbar tick age ──────────────────────────────────────────────────────

    @app.callback(
        Output("navbar-tick-age", "children"),
        Input("main-interval", "n_intervals"),
        State("db-path", "value"),
    )
    def update_tick_age(_, db_path):
        if not db_path:
            return ""
        try:
            prices = load_price_ticks(db_path)
            last = last_db_tick_ts(prices)
            if last is None:
                return "no ticks yet"
            import datetime as dt
            age = max(0.0, (pd.Timestamp.now(tz="UTC") - last).total_seconds())
            if age < 60:
                return f"last tick {age:.0f}s ago"
            return f"last tick {age / 60:.1f}m ago"
        except Exception:
            return ""

    # ── status rail ──────────────────────────────────────────────────────────

    @app.callback(
        Output("status-rail", "children"),
        Input("main-interval", "n_intervals"),
        State("db-path", "value"),
        State("asset-focus", "value"),
    )
    def update_status_rail(_, db_path, asset_focus):
        if not db_path:
            return "No DB path set."
        try:
            prices = load_price_ticks(db_path)
            positions = load_positions(db_path)

            def last_px(pid):
                df = prices[prices["product_id"] == pid] if not prices.empty else pd.DataFrame()
                if df.empty: return None
                return float(df.sort_values("ts").iloc[-1]["price"])

            btc = last_px("BTC-USD")
            eth = last_px("ETH-USD")

            total_realized = float(positions["realized_pnl"].sum()) if not positions.empty else 0.0
            total_unreal = build_unrealized_pnl(positions, btc, eth)
            total_pnl = total_realized + total_unreal

            last = last_db_tick_ts(prices)
            if last is not None:
                age = max(0.0, (pd.Timestamp.now(tz="UTC") - last).total_seconds())
                age_str = f"{age:.0f}s" if age < 60 else f"{age / 60:.1f}m"
            else:
                age_str = "—"

            return html.Div(className="stat-row", children=[
                _stat("BTC", f"${btc:,.2f}" if btc else "—"),
                _stat("ETH", f"${eth:,.2f}" if eth else "—"),
                _stat("Realized", _fmt_money(total_realized), _pnl_color(total_realized)),
                _stat("Unrealized", _fmt_money(total_unreal), _pnl_color(total_unreal)),
                _stat("Total PnL", _fmt_money(total_pnl), _pnl_color(total_pnl)),
                _stat("Tick age", age_str),
            ])
        except Exception as ex:
            return html.Div(f"Error loading status: {ex}", className="alert alert-warning")

    # ── price chart ──────────────────────────────────────────────────────────

    @app.callback(
        Output("price-chart", "figure"),
        Input("main-interval", "n_intervals"),
        State("db-path", "value"),
        State("asset-focus", "value"),
        State("chart-type", "value"),
        State("candle-interval", "value"),
        State("last-n-ticks", "value"),
        State("display-options", "value"),
        State("event-limit", "value"),
        State("event-levels", "value"),
        State("event-search", "value"),
    )
    def update_price_chart(_, db_path, asset_focus, chart_type, candle_interval,
                           last_n_ticks, display_options, event_limit, event_levels, event_search):
        if not db_path:
            return price_line_fig(pd.DataFrame(), "all", 500)
        try:
            prices = load_price_ticks(db_path)
            overlays, signals_only, _ = _get_opts(display_options)

            if chart_type == "candlestick":
                fig = price_candle_fig(prices, asset_focus or "all",
                                       int(last_n_ticks or 500), candle_interval or "5m")
            else:
                fig = price_line_fig(prices, asset_focus or "all", int(last_n_ticks or 500))

            if overlays:
                events = load_events(db_path, limit=int(event_limit or 500))
                events = apply_events_filters(
                    events=events, asset_focus=asset_focus or "all",
                    only_signals=signals_only,
                    levels=set(event_levels or ["info", "warn"]),
                    event_types=set(), text_query=event_search or "",
                )
                fig = add_trade_overlays(fig, prices, events, asset_focus or "all")
            return fig
        except Exception as ex:
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.add_annotation(text=f"Error: {ex}", showarrow=False)
            return fig

    # ── equity chart ─────────────────────────────────────────────────────────

    @app.callback(
        Output("equity-chart", "figure"),
        Input("main-interval", "n_intervals"),
        State("db-path", "value"),
    )
    def update_equity_chart(_, db_path):
        if not db_path:
            return equity_fig(pd.DataFrame())
        try:
            prices = load_price_ticks(db_path)
            positions = load_positions(db_path)
            eq = load_equity_curve(prices, positions)
            return equity_fig(eq)
        except Exception as ex:
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.add_annotation(text=f"Error: {ex}", showarrow=False)
            return fig

    # ── positions table ──────────────────────────────────────────────────────

    @app.callback(
        Output("positions-table", "data"),
        Output("positions-table", "columns"),
        Input("main-interval", "n_intervals"),
        State("db-path", "value"),
        State("asset-focus", "value"),
    )
    def update_positions(_, db_path, asset_focus):
        if not db_path:
            return [], []
        try:
            prices = load_price_ticks(db_path)
            positions = load_positions(db_path)
            pos = compute_asset_pnl_rows(prices, positions)
            pos = apply_asset_focus(pos, asset_focus or "all")
            cols_to_show = ["product_id", "state", "base_qty", "avg_entry",
                            "last_price", "total_pnl", "tp1_done", "tp2_done", "stop_done"]
            pos = pos[[c for c in cols_to_show if c in pos.columns]]
            for c in ["base_qty", "avg_entry", "last_price", "total_pnl"]:
                if c in pos.columns:
                    pos[c] = pos[c].apply(lambda v: f"{v:,.4f}" if c == "base_qty" else f"${v:,.2f}")
            return _df_to_records(pos)
        except Exception:
            return [], []

    # ── orders table ─────────────────────────────────────────────────────────

    @app.callback(
        Output("orders-table", "data"),
        Output("orders-table", "columns"),
        Input("main-interval", "n_intervals"),
        State("db-path", "value"),
        State("asset-focus", "value"),
    )
    def update_orders(_, db_path, asset_focus):
        if not db_path:
            return [], []
        try:
            orders = load_orders(db_path)
            orders = apply_asset_focus(orders, asset_focus or "all")
            return _df_to_records(orders)
        except Exception:
            return [], []

    # ── events table ─────────────────────────────────────────────────────────

    @app.callback(
        Output("events-table", "data"),
        Output("events-table", "columns"),
        Input("main-interval", "n_intervals"),
        State("db-path", "value"),
        State("asset-focus", "value"),
        State("event-limit", "value"),
        State("event-levels", "value"),
        State("event-search", "value"),
        State("display-options", "value"),
    )
    def update_events(_, db_path, asset_focus, event_limit,
                      event_levels, event_search, display_options):
        if not db_path:
            return [], []
        try:
            _, signals_only, _ = _get_opts(display_options)
            events = load_events(db_path, limit=int(event_limit or 500))
            events = apply_events_filters(
                events=events, asset_focus=asset_focus or "all",
                only_signals=signals_only,
                levels=set(event_levels or ["info", "warn"]),
                event_types=set(), text_query=event_search or "",
            )
            if "ts" in events.columns:
                events = events.copy()
                events["ts"] = events["ts"].astype(str).str[:19]
            return _df_to_records(events.head(500))
        except Exception:
            return [], []

    # ── diagnostics ──────────────────────────────────────────────────────────

    @app.callback(
        Output("diagnostics-content", "children"),
        Input("main-interval", "n_intervals"),
        State("db-path", "value"),
    )
    def update_diagnostics(_, db_path):
        if not db_path:
            return "No DB path."
        try:
            prices = load_price_ticks(db_path)
            events = load_events(db_path, limit=500)
            orders = load_orders(db_path)
            positions = load_positions(db_path)
            rows = [
                ("db_path", db_path),
                ("prices_rows", str(len(prices))),
                ("events_rows", str(len(events))),
                ("orders_rows", str(len(orders))),
                ("positions_rows", str(len(positions))),
            ]
            return html.Table([
                html.Tbody([
                    html.Tr([
                        html.Td(k, style={"color": "#8b949e", "fontSize": "0.75rem",
                                          "paddingRight": "1.5rem", "paddingBottom": "4px"}),
                        html.Td(v, style={"color": "#8b949e", "fontSize": "0.75rem",
                                          "fontFamily": "monospace"}),
                    ]) for k, v in rows
                ])
            ])
        except Exception as ex:
            return html.Div(f"Error: {ex}", className="alert alert-warning")

    # ── engine controls ───────────────────────────────────────────────────────

    @app.callback(
        Output("engine-status-text", "children"),
        Output("engine-status-text", "className"),
        Output("engine-pid-text", "children"),
        Output("engine-est-runtime", "children"),
        Output("engine-cmd-preview", "children"),
        Output("engine-navbar-pill", "children"),
        Input("main-interval", "n_intervals"),
        State("engine-mode", "value"),
        State("replay-speed", "value"),
        State("history-csv-path", "value"),
        State("db-path", "value"),
    )
    def update_engine_status(_, mode, speed, history_csv, db_path):
        status = get_engine_status()
        running = status.get("running", False)

        if running:
            status_text = f"● Running (PID {status['pid']})"
            status_class = "engine-running"
            pid_text = f"Started: {status.get('started_at_utc', '')}"
        else:
            status_text = "● Stopped"
            status_class = "engine-stopped"
            pid_text = ""

        # est runtime
        est_text = ""
        if mode == "csv" and history_csv and speed:
            from dashboard.history_manager import load_history_summary
            import datetime as dt
            summary = load_history_summary(history_csv)
            if summary.exists and summary.start_utc and summary.end_utc:
                try:
                    s = dt.datetime.fromisoformat(summary.start_utc)
                    e = dt.datetime.fromisoformat(summary.end_utc)
                    if s.tzinfo is None: s = s.replace(tzinfo=dt.timezone.utc)
                    if e.tzinfo is None: e = e.replace(tzinfo=dt.timezone.utc)
                    sim_s = (e - s).total_seconds()
                    real_s = sim_s / float(speed)
                    est_text = f"Est. runtime: {real_s:.0f}s ({real_s / 60:.1f}m)"
                except Exception:
                    pass

        # cmd preview
        base = ["python", "paper_trader.py", "--db", str(db_path or "")]
        if mode == "demo_rich":
            args = [*base, "--feed", "demo", "--ui", "rich"]
        elif mode == "demo_console":
            args = [*base, "--feed", "demo", "--ui", "console"]
        else:
            args = [*base, "--feed", "csv", "--history-csv", str(history_csv or ""),
                    "--replay", "--speed", str(speed or 3600), "--loop", "--ui", "rich"]
        cmd_text = " ".join(args)

        pill = html.Span(
            "● running" if running else "● stopped",
            className="nav-pill nav-pill-running" if running else "nav-pill nav-pill-stopped",
        )
        return status_text, status_class, pid_text, est_text, cmd_text, pill

    @app.callback(
        Output("engine-action-msg", "children"),
        Input("btn-start-engine", "n_clicks"),
        Input("btn-stop-engine", "n_clicks"),
        State("engine-mode", "value"),
        State("replay-speed", "value"),
        State("history-csv-path", "value"),
        State("db-path", "value"),
        prevent_initial_call=True,
    )
    def engine_action(start_clicks, stop_clicks, mode, speed, history_csv, db_path):
        from dash import ctx
        if not ctx.triggered:
            return no_update

        triggered = ctx.triggered[0]["prop_id"]

        if "btn-start-engine" in triggered:
            try:
                base = ["--db", str(db_path or "runtime/db/paper_trader.db")]
                if mode == "demo_rich":
                    args = [*base, "--feed", "demo", "--ui", "rich"]
                elif mode == "demo_console":
                    args = [*base, "--feed", "demo", "--ui", "console"]
                else:
                    args = [*base, "--feed", "csv", "--history-csv", str(history_csv or ""),
                            "--replay", "--speed", str(speed or 3600), "--loop", "--ui", "rich"]
                res = start_engine(args)
                if res.get("ok"):
                    return _alert(f"Engine started (PID {res['pid']})", "success")
                return _alert(res.get("message", "Failed to start"), "danger")
            except Exception as ex:
                import traceback
                return _alert(f"Exception: {ex} | {traceback.format_exc()[-300:]}", "danger")

        if "btn-stop-engine" in triggered:
            try:
                res = stop_engine()
                if res.get("ok"):
                    return _alert(res.get("message", "Stopped"), "success")
                return _alert(res.get("message", "Failed to stop"), "danger")
            except Exception as ex:
                return _alert(f"Exception: {ex}", "danger")

        return no_update

    # ── history tab ──────────────────────────────────────────────────────────

    @app.callback(
        Output("history-summary", "children"),
        Input("main-interval", "n_intervals"),
        State("history-csv-path", "value"),
    )
    def update_history_summary(_, csv_path):
        if not csv_path:
            return "No path set."
        try:
            from dashboard.history_manager import load_history_summary, load_history_preview
            s = load_history_summary(csv_path)
            if not s.exists:
                return html.Div(f"File not found: {csv_path}", className="alert alert-warning")
            head, tail = load_history_preview(csv_path, n=8)
            hd, hc = _df_to_records(head)
            td, tc = _df_to_records(tail)
            return html.Div([
                html.Div(className="stat-row", style={"marginBottom": "12px"}, children=[
                    _stat("Rows", f"{s.rows:,}"),
                    _stat("Unique ticks", f"{s.unique_ticks:,}"),
                    _stat("Products", str(len(s.products))),
                    _stat("Size", f"{s.size_bytes / 1024 / 1024:.2f} MB"),
                ]),
                html.Div(f"Range: {s.start_utc} → {s.end_utc}",
                         style={"fontSize": "0.75rem", "color": "#8b949e", "marginBottom": "1rem"}),
                html.Div(style={"display": "flex", "gap": "12px"}, children=[
                    html.Div(style={"flex": "1"}, children=[
                        html.Div("Head", style={"fontSize": "0.62rem", "color": _C["sub"], "marginBottom": "4px"}),
                        dash_table.DataTable(data=hd, columns=hc, page_size=8),
                    ]),
                    html.Div(style={"flex": "1"}, children=[
                        html.Div("Tail", style={"fontSize": "0.62rem", "color": _C["sub"], "marginBottom": "4px"}),
                        dash_table.DataTable(data=td, columns=tc, page_size=8),
                    ]),
                ]),
            ])
        except Exception as ex:
            return html.Div(f"Error: {ex}", className="alert alert-danger")

    @app.callback(
        Output("hist-gen-output", "children"),
        Input("btn-gen-history", "n_clicks"),
        State("hist-days", "value"),
        State("hist-granularity", "value"),
        State("hist-provider", "value"),
        State("hist-out-path", "value"),
        prevent_initial_call=True,
    )
    def generate_history(n, days, granularity, provider, out_path):
        if not n:
            return no_update
        ok, output = regenerate_history(
            days=int(days or 183), granularity=granularity or "hourly",
            provider=provider or "binance", out_path=out_path or DEFAULT_HISTORY_CSV_PATH,
        )
        color = "success" if ok else "danger"
        return html.Div([
            _alert("Generated ✅" if ok else "Generation failed", color),
            html.Pre(output[-6000:], style={"fontSize": "0.72rem", "color": "#8b949e",
                                            "background": "rgba(0,0,0,0.3)", "padding": "0.75rem",
                                            "borderRadius": "8px", "overflowX": "auto"}),
        ])

    # ── strategy tab ─────────────────────────────────────────────────────────

    @app.callback(
        Output("strategy-summary", "children"),
        Output("strategy-editor", "value"),
        Input("main-interval", "n_intervals"),
        State("strategy-path", "value"),
    )
    def update_strategy_tab(_, strategy_path):
        if not strategy_path:
            return "No path.", ""
        ok, data, err = load_strategy_yaml(strategy_path)
        if not ok or data is None:
            return html.Div(f"Could not load strategy: {err}", className="alert alert-warning"), ""

        bankroll = float(data.get("bankroll_usd", 0))
        assets = data.get("assets", {})
        enabled = [pid for pid, a in assets.items() if a.get("enabled", True)]
        total_alloc = sum(float(a.get("allocation_usd", 0)) for a in assets.values() if a.get("enabled", True))

        summary = html.Div([
            html.Div("Current Strategy", className="card-title"),
            html.Div(className="stat-row", style={"marginBottom": "12px"}, children=[
                _stat("Bankroll", f"${bankroll:,.2f}"),
                _stat("Enabled assets", str(len(enabled))),
                _stat("Total allocated", f"${total_alloc:,.2f}"),
                _stat("Unallocated", f"${bankroll - total_alloc:,.2f}"),
            ]),
        ])

        yaml_text = yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
        return summary, yaml_text

    @app.callback(
        Output("strategy-action-msg", "children"),
        Input("btn-validate-strategy", "n_clicks"),
        Input("btn-save-strategy", "n_clicks"),
        State("strategy-editor", "value"),
        State("strategy-path", "value"),
        prevent_initial_call=True,
    )
    def strategy_action(val_clicks, save_clicks, yaml_text, strategy_path):
        from dash import ctx
        if not ctx.triggered:
            return no_update
        triggered = ctx.triggered[0]["prop_id"]
        try:
            parsed = yaml.safe_load(yaml_text or "")
        except yaml.YAMLError as ex:
            return _alert(f"YAML parse error: {ex}", "danger")

        v_ok, v_err = validate_strategy_dict(parsed)
        if not v_ok:
            return _alert(f"Validation failed: {v_err}", "danger")

        if "btn-validate-strategy" in triggered:
            return _alert("Validation passed ✅", "success")

        if "btn-save-strategy" in triggered:
            s_ok, s_err = save_strategy_yaml(strategy_path or "strategy.yaml", parsed)
            if s_ok:
                return _alert(f"Saved to {strategy_path} ✅ — restart engine to apply.", "success")
            return _alert(f"Save failed: {s_err}", "danger")

        return no_update

    # ── clear data ───────────────────────────────────────────────────────────

    @app.callback(
        Output("clear-data-msg", "children"),
        Output("btn-confirm-clear", "style"),
        Output("store-confirm-clear", "data"),
        Input("btn-clear-data", "n_clicks"),
        Input("btn-confirm-clear", "n_clicks"),
        State("db-path", "value"),
        State("store-confirm-clear", "data"),
        prevent_initial_call=True,
    )
    def handle_clear(clear_clicks, confirm_clicks, db_path, awaiting_confirm):
        from dash import ctx
        if not ctx.triggered:
            return no_update, no_update, no_update
        triggered = ctx.triggered[0]["prop_id"]

        if "btn-clear-data" in triggered:
            return (_alert("Click 'Confirm Clear' to proceed.", "warning"),
                    {"display": "block"}, True)

        if "btn-confirm-clear" in triggered and awaiting_confirm:
            try:
                clear_all_data(db_path)
                load_price_ticks.clear()
                load_positions.clear()
                load_orders.clear()
                load_events.clear()
                return _alert("Cleared ✅", "success"), {"display": "none"}, False
            except Exception as ex:
                return _alert(f"Failed: {ex}", "danger"), {"display": "none"}, False

        return no_update, no_update, no_update

    # ── reports tab ───────────────────────────────────────────────────────────

    @app.callback(
        Output("reports-config-display", "children"),
        Input("main-interval", "n_intervals"),
        State("db-path", "value"),
        State("strategy-path", "value"),
    )
    def update_reports_config(_, db_path, strategy_path):
        return html.Div([
            html.Div(f"DB: {db_path}", style={"fontSize": "0.75rem", "color": "#8b949e"}),
            html.Div(f"Strategy: {strategy_path}", style={"fontSize": "0.75rem", "color": "#8b949e"}),
        ])

    @app.callback(
        Output("store-report-bundle", "data"),
        Output("reports-build-msg", "children"),
        Output("reports-kpi-row", "children"),
        Input("btn-build-report", "n_clicks"),
        State("db-path", "value"),
        State("strategy-path", "value"),
        State("reports-save-snapshot", "value"),
        prevent_initial_call=True,
    )
    def build_report(n, db_path, strategy_path, save_opts):
        if not n:
            return no_update, no_update, no_update
        try:
            bundle = _build_report_bundle(db_path=db_path, strategy_config_path=strategy_path)
            msg = _alert(f"Report built — hash: {bundle.strategy_hash[:12]}…", "success")

            if "save" in (save_opts or []):
                ok, save_msg = _save_report_snapshot(bundle=bundle, db_path=db_path, strategy_path=strategy_path)
                if not ok:
                    msg = _alert(f"Built but snapshot failed: {save_msg}", "warning")

            total_pnl = _summary_value(bundle, "total_pnl")
            realized = _summary_value(bundle, "total_realized_pnl")
            unreal = _summary_value(bundle, "total_unrealized_pnl")
            max_dd = _summary_value(bundle, "max_drawdown")
            entries = _summary_value(bundle, "entries_filled") or 0
            stops = _summary_value(bundle, "stops_filled") or 0
            tp2 = _summary_value(bundle, "tp2_filled") or 0
            stop_rate = float(stops) / float(entries) if entries else None
            tp2_rate = float(tp2) / float(entries) if entries else None

            kpi_row = html.Div(className="card", children=[
                html.Div(className="stat-row", children=[
                    _stat("Total PnL", _fmt_money(total_pnl), _pnl_color(total_pnl or 0)),
                    _stat("Realized", _fmt_money(realized), _pnl_color(realized or 0)),
                    _stat("Unrealized", _fmt_money(unreal), _pnl_color(unreal or 0)),
                    _stat("Max Drawdown", _fmt_money(max_dd)),
                    _stat("Stop rate", _fmt_pct(stop_rate)),
                    _stat("TP2 rate", _fmt_pct(tp2_rate)),
                ]),
            ])

            # serialise bundle for storage (DataFrames → JSON)
            bundle_data = {
                "summary": bundle.summary.to_json(),
                "equity": bundle.equity.to_json(),
                "events": bundle.events.to_json(),
                "orders": bundle.orders.to_json(),
                "positions": bundle.positions.to_json(),
                "trades": bundle.trades.to_json() if not bundle.trades.empty else "{}",
                "strategy_yaml_text": bundle.strategy_yaml_text,
                "strategy_hash": bundle.strategy_hash,
            }
            return bundle_data, msg, kpi_row

        except Exception as ex:
            return no_update, _alert(f"Build failed: {ex}", "danger"), no_update

    def _restore_bundle(bundle_data: dict):
        """Deserialise the stored bundle dict back to a ReportBundle-like object."""
        from dashboard.ui_parts.render_reports import ReportBundle
        if not bundle_data:
            return None

        def _load(key):
            raw = bundle_data.get(key, "{}")
            try:
                df = pd.read_json(io.StringIO(raw))
                if "ts" in df.columns:
                    df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
                return df
            except Exception:
                return pd.DataFrame()

        return ReportBundle(
            summary=_load("summary"),
            equity=_load("equity"),
            events=_load("events"),
            orders=_load("orders"),
            positions=_load("positions"),
            trades=_load("trades"),
            strategy_yaml_text=bundle_data.get("strategy_yaml_text", ""),
            strategy_hash=bundle_data.get("strategy_hash", ""),
        )

    @app.callback(
        Output("report-summary-content", "children"),
        Output("report-trades-content", "children"),
        Output("report-equity-content", "children"),
        Output("report-events-content", "children"),
        Output("report-exports-content", "children"),
        Output("report-compare-content", "children"),
        Input("store-report-bundle", "data"),
    )
    def render_report_tabs(bundle_data):
        if not bundle_data:
            empty = html.Div("Click 'Build Report' to generate.", className="alert alert-secondary")
            return empty, empty, empty, empty, empty, empty

        bundle = _restore_bundle(bundle_data)
        if bundle is None:
            err = html.Div("Could not restore report data.", className="alert alert-danger")
            return err, err, err, err, err, err

        # ── summary ──
        sd, sc = _df_to_records(bundle.summary)
        summary_content = html.Div(className="card", children=[dash_table.DataTable(
            data=sd, columns=sc, page_size=20,
        )])

        # ── trades ──
        if bundle.trades.empty:
            trades_content = html.Div("No reconstructed trades yet.", className="alert alert-secondary")
        else:
            td, tc = _df_to_records(bundle.trades.tail(75))
            trades_content = html.Div([
                dash_table.DataTable(data=td, columns=tc, page_size=20, sort_action="native",
                                     style_cell={"background": "transparent", "color": "#8b949e",
                                                 "fontSize": "12px", "border": "none",
                                                 "fontFamily": "'DM Mono', monospace"},
                                     style_header={"background": "rgba(255,255,255,0.04)",
                                                   "color": "#8b949e", "fontSize": "11px",
                                                   "border": "none"}),
                html.Div(className="card", style={"marginTop": "12px"},
                         children=[dcc.Graph(figure=trades_bar_fig(bundle.trades),
                                             config=PLOTLY_CONFIG)]),
            ])

        # ── equity ──
        equity_content = html.Div([
            html.Div(className="card",
                     children=[dcc.Graph(figure=equity_fig(bundle.equity), config=PLOTLY_CONFIG)]),
        ])

        # ── events ──
        if bundle.events.empty:
            events_content = html.Div("No events.", className="alert alert-secondary")
        else:
            ed, ec = _df_to_records(bundle.events.head(300))
            events_content = html.Div(style={"display": "flex", "gap": "12px"}, children=[
                html.Div(style={"flex": "4"}, children=[
                    dcc.Graph(figure=event_bar_fig(bundle.events), config=PLOTLY_CONFIG),
                ]),
                html.Div(style={"flex": "8"}, children=[
                    dash_table.DataTable(data=ed, columns=ec, page_size=20),
                ]),
            ])

        # ── exports ──
        zip_bytes = _build_zip_bundle(bundle)
        exports_content = html.Div([
            html.Div("Download Report Bundle", style={"fontSize": "0.72rem", "color": "#8b949e",
                                                      "marginBottom": "0.75rem"}),
            dcc.Download(id="download-zip"),
            html.Button("Download ZIP", id="btn-download-zip", n_clicks=0, className="btn btn-amber btn-sm"),
            html.Hr(style={"borderColor": "rgba(255,255,255,0.07)", "margin": "1rem 0"}),
            html.Div("Strategy Snapshot", style={"fontSize": "0.72rem", "color": "#8b949e",
                                                 "marginBottom": "0.5rem"}),
            html.Pre(bundle.strategy_yaml_text,
                     style={"fontSize": "0.72rem", "color": "#8b949e", "background": "rgba(0,0,0,0.3)",
                            "padding": "0.75rem", "borderRadius": "8px", "overflowX": "auto"}),
        ])

        # ── compare ──
        saved = _list_saved_reports()
        if not saved:
            compare_content = html.Div("No saved snapshots yet. Enable 'Save snapshot to disk' and build.",
                                       className="alert alert-secondary")
        else:
            labels = []
            by_label = {}
            for r in saved:
                k = r.get("kpis") or {}
                pnl = k.get("total_pnl")
                lbl = f"{r['created_at_utc']}  ·  {r['strategy_hash']}  ·  pnl={_fmt_money(pnl)}"
                labels.append(lbl)
                by_label[lbl] = r

            opts = [{"label": l, "value": l} for l in labels]
            base_default = labels[min(1, len(labels) - 1)]
            cand_default = labels[0]

            base_r = by_label[base_default]
            cand_r = by_label[cand_default]
            base_l = _load_saved_report(base_r["zip_path"])
            cand_l = _load_saved_report(cand_r["zip_path"])

            kpi_df = _build_kpi_compare_table(
                base_l.get("meta", {}), cand_l.get("meta", {}))
            kd, kc = _df_to_records(kpi_df)

            compare_content = html.Div([
                html.Div(style={"display": "flex", "gap": "12px", "marginBottom": "12px"}, children=[
                    html.Div(style={"flex": "1"}, children=[
                        html.Div("Baseline", style={"fontSize": "0.60rem", "color": _C["sub"], "marginBottom": "4px"}),
                        dcc.Dropdown(id="compare-base", options=opts, value=base_default, clearable=False),
                    ]),
                    html.Div(style={"flex": "1"}, children=[
                        html.Div("Candidate", style={"fontSize": "0.60rem", "color": _C["sub"], "marginBottom": "4px"}),
                        dcc.Dropdown(id="compare-cand", options=opts, value=cand_default, clearable=False),
                    ]),
                ]),
                html.Div(className="card", children=[
                    html.Div("KPI Diff", className="card-title"),
                    dash_table.DataTable(data=kd, columns=kc),
                ]),
                html.Div(className="card", style={"marginTop": "12px"}, children=[
                    html.Div("Equity Overlay", className="card-title"),
                    dcc.Graph(
                        figure=equity_compare_fig(
                            base_l.get("equity", pd.DataFrame()),
                            cand_l.get("equity", pd.DataFrame()),
                        ),
                        config=PLOTLY_CONFIG,
                    ),
                ]),
            ])

        return summary_content, trades_content, equity_content, events_content, exports_content, compare_content

    @app.callback(
        Output("download-zip", "data"),
        Input("btn-download-zip", "n_clicks"),
        State("store-report-bundle", "data"),
        prevent_initial_call=True,
    )
    def download_zip(n, bundle_data):
        if not n or not bundle_data:
            return no_update
        bundle = _restore_bundle(bundle_data)
        if bundle is None:
            return no_update
        from dashboard.ui_parts.render_reports import _build_zip_bundle
        zip_bytes = _build_zip_bundle(bundle)
        fname = f"qye_report_{bundle.strategy_hash[:10]}.zip"
        return dcc.send_bytes(zip_bytes, fname)
