# dashboard_dash/components.py
"""Layout + CSS. Zero Bootstrap. Purple theme. Single source of truth."""
from __future__ import annotations

from dash import dcc, html, dash_table

from dashboard.constants import (
    DEFAULT_RUNTIME_DB_PATH,
    DEFAULT_HISTORY_CSV_PATH,
    DEFAULT_STRATEGY_PATH,
)

# ── Colour tokens ─────────────────────────────────────────────────────────────
PRIMARY   = "#a78bfa"   # violet-400  — main accent
PRIMARY2  = "#c4b5fd"   # violet-300  — softer accent
PRIMARY_DIM = "rgba(167,139,250,0.15)"
PRIMARY_GLOW = "rgba(167,139,250,0.08)"
CYAN      = "#22d3ee"
GREEN     = "#34d399"
RED       = "#fb7185"
AMBER     = "#fbbf24"
BLUE      = "#60a5fa"

TEXT      = "#e5e7eb"   # gray-200
TEXT_MUTED = "rgba(255,255,255,0.50)"
BG        = "#0b1020"   # deep navy
SURF      = "#101833"   # panel surface
SURF2     = "#0d1428"   # slightly deeper panel
BORDER    = "rgba(167,139,250,0.12)"
BORDER_BRIGHT = "rgba(167,139,250,0.28)"
MONO      = "'DM Mono','Menlo',monospace"

# ── CSS string ────────────────────────────────────────────────────────────────
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:ital,wght@0,300;0,400;0,500;1,400&family=DM+Sans:wght@400;500;600;700&display=swap');

/* ── reset ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { font-size: 15px; }
body {
  background: #0b1020 !important;
  color: #e5e7eb !important;
  font-family: 'DM Sans', sans-serif !important;
  -webkit-font-smoothing: antialiased;
}

/* ── scrollbar ── */
* { scrollbar-width: thin; scrollbar-color: rgba(167,139,250,0.20) transparent; }
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-thumb { background: rgba(167,139,250,0.22); border-radius: 2px; }

/* ── dash chrome ── */
._dash-loading, .dash-debug-menu, .dash-update-title { display: none !important; }

/* ══════════════════════════════════════════════════════
   NAVBAR
══════════════════════════════════════════════════════ */
.navbar {
  height: 48px;
  background: #0d1428;
  border-bottom: 1px solid rgba(167,139,250,0.14);
  display: flex; align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  position: sticky; top: 0; z-index: 200;
  flex-shrink: 0;
  box-shadow: 0 1px 24px rgba(0,0,0,0.4);
}
.navbar-brand {
  font-family: 'DM Sans', sans-serif;
  font-size: 0.88rem; font-weight: 700;
  letter-spacing: 0.18em; text-transform: uppercase;
  color: #a78bfa;
  display: flex; align-items: center; gap: 8px;
}
.navbar-brand .dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: #a78bfa;
  box-shadow: 0 0 8px rgba(167,139,250,0.7);
  animation: pulse-dot 2.4s ease-in-out infinite;
  flex-shrink: 0;
}
@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.55; transform: scale(0.75); }
}
.navbar-brand .dim { color: rgba(167,139,250,0.45); font-weight: 400; margin: 0 1px; }
.navbar-right { display: flex; align-items: center; gap: 16px; }
.nav-pill {
  font-family: 'DM Mono', monospace;
  font-size: 0.67rem; font-weight: 500;
  letter-spacing: 0.08em; text-transform: uppercase;
  padding: 3px 10px; border-radius: 20px;
}
.nav-pill-running {
  color: #34d399;
  background: rgba(52,211,153,0.10);
  border: 1px solid rgba(52,211,153,0.30);
}
.nav-pill-stopped {
  color: rgba(255,255,255,0.35);
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
}
.nav-tick {
  font-family: 'DM Mono', monospace;
  font-size: 0.72rem; color: rgba(255,255,255,0.35);
}

/* ══════════════════════════════════════════════════════
   LAYOUT
══════════════════════════════════════════════════════ */
.body-wrap { display: flex; min-height: calc(100vh - 48px); }
.main {
  flex: 1; min-width: 0;
  background: #0b1020;
  padding: 14px 18px 24px;
  overflow-y: auto;
}

/* ══════════════════════════════════════════════════════
   SIDEBAR
══════════════════════════════════════════════════════ */
.sidebar {
  width: 228px; min-width: 228px;
  background: #0d1428;
  border-right: 1px solid rgba(167,139,250,0.10);
  padding: 10px 12px 32px;
  overflow-y: auto; overflow-x: hidden;
  flex-shrink: 0;
}

/* Section headers */
.sb-head {
  font-family: 'DM Sans', sans-serif;
  font-size: 0.74rem; font-weight: 700;
  color: #a78bfa;
  text-transform: uppercase; letter-spacing: 0.20em;
  padding: 18px 2px 6px;
  border-bottom: 1px solid rgba(167,139,250,0.16);
  margin-bottom: 10px;
}
.sb-head:first-child { padding-top: 6px; }

/* Field labels */
.sb-label {
  font-family: 'DM Mono', monospace;
  font-size: 0.70rem; color: rgba(255,255,255,0.50);
  text-transform: uppercase; letter-spacing: 0.10em;
  margin: 10px 0 4px;
}

/* ── sidebar text inputs ── */
.sidebar input[type=text],
.sidebar input[type=number],
.sidebar .dash-input input {
  width: 100% !important;
  background: rgba(11,16,32,0.8) !important;
  border: 1px solid rgba(167,139,250,0.18) !important;
  border-radius: 6px !important;
  color: #e5e7eb !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 0.78rem !important;
  padding: 5px 9px !important;
  height: 30px !important;
  outline: none !important;
  transition: border-color 0.15s !important;
}
.sidebar input[type=text]:focus,
.sidebar input[type=number]:focus,
.sidebar .dash-input input:focus {
  border-color: #a78bfa !important;
  box-shadow: 0 0 0 2px rgba(167,139,250,0.15) !important;
}
.sidebar .dash-input { display: block !important; }

/* ── SLIDERS ── */
.rc-slider { margin: 10px 4px 18px; }
.rc-slider-rail  { background: rgba(167,139,250,0.12) !important; height: 3px !important; border-radius: 2px !important; }
.rc-slider-track { background: #a78bfa !important; height: 3px !important; border-radius: 2px !important; }
.rc-slider-step  { background: transparent !important; }
.rc-slider-dot   { display: none !important; }
.rc-slider-handle {
  width: 13px !important; height: 13px !important;
  background: #0b1020 !important;
  border: 2px solid #a78bfa !important;
  border-radius: 50% !important;
  margin-top: -5px !important;
  box-shadow: none !important;
  opacity: 1 !important;
  cursor: pointer !important;
}
.rc-slider-handle-dragging,
.rc-slider-handle:hover {
  border-color: #c4b5fd !important;
  box-shadow: 0 0 0 3px rgba(167,139,250,0.22) !important;
}
.rc-slider-tooltip-inner {
  background: #101833 !important;
  border: 1px solid rgba(167,139,250,0.20) !important;
  color: #e5e7eb !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 0.62rem !important;
  padding: 2px 6px !important;
  border-radius: 4px !important;
  box-shadow: none !important;
}
.rc-slider-mark-text { color: rgba(167,139,250,0.30) !important; font-size: 0.57rem !important; }

/* ── CHECKBOXES ── */
input[type=checkbox] {
  -webkit-appearance: none !important;
  appearance: none !important;
  width: 13px !important; height: 13px !important;
  border: 1.5px solid rgba(167,139,250,0.30) !important;
  border-radius: 3px !important;
  background: rgba(11,16,32,0.8) !important;
  cursor: pointer !important;
  flex-shrink: 0 !important;
  vertical-align: middle !important;
  margin-right: 6px !important;
  position: relative !important;
  display: inline-block !important;
  transition: background .12s, border-color .12s !important;
}
input[type=checkbox]:checked {
  background: #a78bfa !important;
  border-color: #a78bfa !important;
}
input[type=checkbox]:checked::after {
  content: '' !important;
  display: block !important;
  position: absolute !important;
  left: 3px !important; top: 0px !important;
  width: 4px !important; height: 8px !important;
  border: 1.5px solid #0b1020 !important;
  border-top: none !important; border-left: none !important;
  transform: rotate(45deg) !important;
}

/* ── DROPDOWNS (react-select v3+) ── */
.sidebar .dash-dropdown { margin-bottom: 4px; }
.sidebar [class$="-control"], .sidebar [class*=" -control"],
.sidebar [class*="-control"] {
  background: rgba(11,16,32,0.8) !important;
  border: 1px solid rgba(167,139,250,0.18) !important;
  border-radius: 6px !important;
  min-height: 30px !important;
  box-shadow: none !important;
  cursor: pointer !important;
  transition: border-color 0.15s !important;
}
.sidebar [class$="-control"]:hover,
.sidebar [class*="-control"]:hover { border-color: #a78bfa !important; }
.sidebar [class*="singleValue"] {
  color: #e5e7eb !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 0.78rem !important;
}
.sidebar [class*="placeholder"] {
  color: rgba(255,255,255,0.30) !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 0.78rem !important;
}
.sidebar [class*="indicatorSeparator"] { display: none !important; }
.sidebar [class*="dropdownIndicator"] svg {
  fill: rgba(167,139,250,0.45) !important;
  width: 12px !important; height: 12px !important;
}
/* Menu portal renders outside .sidebar so target globally */
[class*="-menu"], [class$="-menu"] {
  background: #0d1a38 !important;
  border: 1px solid rgba(167,139,250,0.25) !important;
  border-radius: 6px !important;
  z-index: 9999 !important;
  box-shadow: 0 12px 32px rgba(0,0,0,0.75) !important;
}
[class*="-MenuList"], [class$="-MenuList"] {
  background: #0d1a38 !important;
  padding: 4px !important;
}
[class*="-option"], [class$="-option"] {
  background: transparent !important;
  color: #e5e7eb !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 0.78rem !important;
  padding: 6px 10px !important;
  cursor: pointer !important;
  border-radius: 4px !important;
}
[class*="-option"]:hover,
[class*="option--is-focused"],
[class$="option--is-focused"] {
  background: rgba(167,139,250,0.12) !important;
  color: #c4b5fd !important;
}
[class*="option--is-selected"],
[class$="option--is-selected"] {
  background: rgba(167,139,250,0.20) !important;
  color: #a78bfa !important;
}
.sidebar [class*="ValueContainer"] {
  padding: 0 8px !important;
  min-height: 28px !important;
}
.sidebar [class*="Input"] input {
  color: #e5e7eb !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 0.78rem !important;
}

/* ── sidebar engine status ── */
.engine-running {
  color: #34d399; font-size: 0.80rem; font-weight: 600;
  font-family: 'DM Mono', monospace;
}
.engine-stopped {
  color: rgba(255,255,255,0.35); font-size: 0.80rem;
  font-family: 'DM Mono', monospace;
}

/* ══════════════════════════════════════════════════════
   TABS  (main nav + inner sub-tabs)
══════════════════════════════════════════════════════ */
.custom-tabs .tab {
  font-family: 'DM Sans', sans-serif !important;
  font-size: 0.80rem !important; font-weight: 500 !important;
  text-transform: uppercase !important; letter-spacing: 0.10em !important;
  padding: 11px 18px !important;
  border: none !important;
  border-bottom: 2px solid transparent !important;
  background: transparent !important;
  color: rgba(255,255,255,0.40) !important;
  cursor: pointer; white-space: nowrap;
  transition: color .15s, border-color .15s;
}
.custom-tabs .tab:hover { color: rgba(255,255,255,0.75) !important; }
.custom-tabs .tab--selected {
  color: #c4b5fd !important;
  border-bottom: 2px solid #a78bfa !important;
}
.custom-tabs .tab-container {
  border-bottom: 1px solid rgba(167,139,250,0.12) !important;
  background: transparent !important;
  overflow-x: auto;
}
.custom-tabs .tab-content { padding-top: 2px !important; }

/* Inner report sub-tabs — slightly smaller */
.report-tabs .tab {
  font-size: 0.65rem !important;
  padding: 8px 14px !important;
}

/* ══════════════════════════════════════════════════════
   CARDS
══════════════════════════════════════════════════════ */
.card {
  background: #101833;
  border: 1px solid rgba(167,139,250,0.10);
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 10px;
  position: relative;
  overflow: hidden;
}
/* Subtle purple top-edge accent */
.card::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, rgba(167,139,250,0.55) 0%, rgba(34,211,238,0.25) 50%, transparent 100%);
}
.card-title {
  font-family: 'DM Mono', monospace;
  font-size: 0.72rem; font-weight: 500;
  color: rgba(167,139,250,0.70);
  text-transform: uppercase; letter-spacing: 0.16em;
  margin-bottom: 10px;
}

/* ══════════════════════════════════════════════════════
   STAT RAIL  (status bar at top)
══════════════════════════════════════════════════════ */
.stat-row {
  display: flex; flex-direction: row;
  border: 1px solid rgba(167,139,250,0.10);
  border-radius: 10px; overflow: hidden;
  margin-bottom: 10px;
  background: #101833;
}
.stat-tile {
  flex: 1; padding: 12px 16px;
  border-right: 1px solid rgba(167,139,250,0.08);
  position: relative;
}
.stat-tile:last-child { border-right: none; }
.stat-label {
  font-family: 'DM Mono', monospace;
  font-size: 0.62rem; font-weight: 500;
  color: rgba(167,139,250,0.55);
  text-transform: uppercase; letter-spacing: 0.14em;
  margin-bottom: 6px;
}
.stat-value {
  font-family: 'DM Mono', monospace;
  font-size: 1.25rem; font-weight: 500;
  color: #e5e7eb; letter-spacing: -0.02em; line-height: 1;
}
.stat-value.pos   { color: #34d399; }
.stat-value.neg   { color: #fb7185; }
.stat-value.amber { color: #fbbf24; }
.stat-value.muted { color: rgba(255,255,255,0.35); }
.stat-value.purple { color: #a78bfa; }

/* ══════════════════════════════════════════════════════
   PLOTLY modebar
══════════════════════════════════════════════════════ */
.modebar-container {
  opacity: 0 !important;
  transition: opacity 0.2s !important;
  background: transparent !important;
}
.js-plotly-plot:hover .modebar-container { opacity: 1 !important; }
.modebar-btn svg {
  width: 14px !important; height: 14px !important;
  fill: rgba(167,139,250,0.45) !important;
}
.modebar-btn:hover svg { fill: #a78bfa !important; }
.modebar-group { background: transparent !important; }

/* ══════════════════════════════════════════════════════
   DATA TABLES
══════════════════════════════════════════════════════ */
.dash-table-container {
  border: 1px solid rgba(167,139,250,0.10) !important;
  border-radius: 8px !important; overflow: hidden !important;
}
.dash-spreadsheet-inner table {
  border-collapse: collapse !important; width: 100% !important;
}
.dash-spreadsheet-inner th {
  background: rgba(13,20,40,0.9) !important;
  color: rgba(167,139,250,0.60) !important;
  font-family: 'DM Mono', monospace !important; font-size: 0.65rem !important;
  font-weight: 500 !important; text-transform: uppercase !important;
  letter-spacing: 0.12em !important;
  border: none !important;
  border-bottom: 1px solid rgba(167,139,250,0.10) !important;
  padding: 9px 14px !important; white-space: nowrap !important;
}
.dash-spreadsheet-inner td {
  background: transparent !important; color: #e5e7eb !important;
  font-family: 'DM Mono', monospace !important; font-size: 0.80rem !important;
  border: none !important;
  border-bottom: 1px solid rgba(167,139,250,0.05) !important;
  padding: 8px 14px !important; white-space: nowrap !important;
}
.dash-spreadsheet-inner tr:hover td {
  background: rgba(167,139,250,0.05) !important;
}
.dash-filter input {
  background: rgba(11,16,32,0.8) !important;
  color: #e5e7eb !important;
  font-family: 'DM Mono', monospace !important; font-size: 0.65rem !important;
  border: none !important;
  border-bottom: 1px solid rgba(167,139,250,0.14) !important;
  outline: none !important; padding: 4px 12px !important;
}

/* ══════════════════════════════════════════════════════
   BUTTONS
══════════════════════════════════════════════════════ */
button, .btn {
  font-family: 'DM Sans', sans-serif !important;
  font-size: 0.75rem !important; font-weight: 600 !important;
  letter-spacing: 0.04em !important;
  border-radius: 6px !important; padding: 7px 15px !important;
  cursor: pointer !important;
  transition: all .15s !important;
  outline: none !important;
}
button:hover, .btn:hover { opacity: 0.82 !important; }
.btn-primary {
  background: #a78bfa !important; color: #0b1020 !important;
  border: none !important; font-weight: 700 !important;
}
.btn-primary:hover { background: #c4b5fd !important; opacity: 1 !important; }
.btn-ghost {
  background: transparent !important; color: #a78bfa !important;
  border: 1px solid rgba(167,139,250,0.35) !important;
}
.btn-ghost:hover {
  background: rgba(167,139,250,0.10) !important;
  border-color: #a78bfa !important;
  opacity: 1 !important;
}
.btn-danger {
  background: rgba(251,113,133,0.12) !important; color: #fb7185 !important;
  border: 1px solid rgba(251,113,133,0.30) !important;
}
.btn-danger:hover {
  background: rgba(251,113,133,0.22) !important;
  opacity: 1 !important;
}
.btn-sm { padding: 5px 11px !important; font-size: 0.70rem !important; }
.w-100 { width: 100% !important; }
.mt-1 { margin-top: 8px !important; }

/* ══════════════════════════════════════════════════════
   ALERTS
══════════════════════════════════════════════════════ */
.alert {
  font-family: 'DM Mono', monospace; font-size: 0.75rem;
  padding: 8px 12px; border-radius: 6px;
  border-left: 3px solid; margin-top: 8px;
  border-top: none; border-right: none; border-bottom: none;
  line-height: 1.5;
}
.alert-success   { background: rgba(52,211,153,0.08);   border-color: #34d399; color: #34d399; }
.alert-danger    { background: rgba(251,113,133,0.08);  border-color: #fb7185; color: #fb7185; }
.alert-warning   { background: rgba(251,191,36,0.08);   border-color: #fbbf24; color: #fbbf24; }
.alert-secondary { background: rgba(167,139,250,0.05);  border-color: rgba(167,139,250,0.25); color: rgba(255,255,255,0.45); }
.alert-info      { background: rgba(167,139,250,0.08);  border-color: #a78bfa;  color: #a78bfa;  }

/* ══════════════════════════════════════════════════════
   TEXTAREA / PRE / CODE
══════════════════════════════════════════════════════ */
textarea {
  width: 100% !important;
  background: rgba(11,16,32,0.85) !important;
  border: 1px solid rgba(167,139,250,0.18) !important;
  border-radius: 8px !important;
  color: #e5e7eb !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 0.72rem !important; padding: 10px !important;
  resize: vertical !important; outline: none !important;
  line-height: 1.6 !important;
}
textarea:focus {
  border-color: #a78bfa !important;
  box-shadow: 0 0 0 2px rgba(167,139,250,0.14) !important;
}
pre, code {
  background: rgba(11,16,32,0.85) !important;
  border: 1px solid rgba(167,139,250,0.12) !important;
  border-radius: 6px !important; color: #e5e7eb !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 0.68rem !important;
  padding: 10px 12px !important; white-space: pre-wrap !important;
  line-height: 1.6 !important;
}

/* ══════════════════════════════════════════════════════
   FLEX GRID
══════════════════════════════════════════════════════ */
.row2 { display: flex; gap: 10px; margin-bottom: 10px; }
.row2 > * { flex: 1; min-width: 0; }
.col-8 { flex: 8 !important; } .col-4 { flex: 4 !important; }
.col-6 { flex: 6 !important; } .col-3 { flex: 3 !important; }
.col-2 { flex: 2 !important; } .col-1 { flex: 1 !important; }
"""

# Dropdown CSS injected AFTER react-select's own stylesheet (before </body>)
# so our rules win without needing !important on every line.
# react-select portals menus to <body>, so .sidebar parent never matches —
# we must use global selectors here.
DROPDOWN_CSS = """
/* ── react-select control (stays inside .sidebar DOM) ── */
.sidebar [class$="-control"],
.sidebar [class*="-control"] {
  background: rgba(11,16,32,0.85) !important;
  border: 1px solid rgba(167,139,250,0.22) !important;
  border-radius: 6px !important;
  min-height: 30px !important;
  box-shadow: none !important;
  cursor: pointer !important;
}
.sidebar [class$="-control"]:hover,
.sidebar [class*="-control"]:hover {
  border-color: #a78bfa !important;
}
.sidebar [class*="singleValue"] {
  color: #e5e7eb !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 0.78rem !important;
}
.sidebar [class*="placeholder"] {
  color: rgba(255,255,255,0.30) !important;
  font-size: 0.78rem !important;
}
.sidebar [class*="indicatorSeparator"] { display: none !important; }
.sidebar [class*="dropdownIndicator"] svg {
  fill: rgba(167,139,250,0.50) !important;
  width: 12px !important; height: 12px !important;
}
.sidebar [class*="ValueContainer"] { padding: 0 8px !important; }
.sidebar [class*="Input"] input {
  color: #e5e7eb !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 0.78rem !important;
}

/* ── Menu portal — portalled to <body>, must be global ── */
div[class$="-menu"],
div[class*="-menu"] {
  background: #0d1220 !important;
  border: 1px solid rgba(167,139,250,0.30) !important;
  border-radius: 8px !important;
  z-index: 99999 !important;
  box-shadow: 0 16px 40px rgba(0,0,0,0.80), 0 0 0 1px rgba(167,139,250,0.10) !important;
  overflow: hidden !important;
}
div[class$="-MenuList"],
div[class*="-MenuList"] {
  background: #0d1220 !important;
  padding: 4px !important;
}
div[class$="-option"],
div[class*="-option"] {
  background: transparent !important;
  color: rgba(229,231,235,0.85) !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 0.80rem !important;
  padding: 7px 12px !important;
  cursor: pointer !important;
  border-radius: 4px !important;
  margin: 1px 2px !important;
}
div[class*="option--is-focused"],
div[class$="option--is-focused"] {
  background: rgba(167,139,250,0.14) !important;
  color: #c4b5fd !important;
}
div[class*="option--is-selected"],
div[class$="option--is-selected"] {
  background: rgba(167,139,250,0.22) !important;
  color: #a78bfa !important;
}
"""


# ── small helpers ─────────────────────────────────────────────────────────────

def _label(t):      return html.Div(t, className="sb-label")
def _head(t):       return html.Div(t, className="sb-head")
def _card_title(t): return html.Div(t, className="card-title")


INPUT_STYLE = dict(
    width="100%",
    background="rgba(11,16,32,0.8)",
    border=f"1px solid {BORDER_BRIGHT}",
    borderRadius="6px",
    color=TEXT,
    fontFamily=MONO,
    fontSize="0.78rem",
    padding="5px 9px",
    height="30px",
    outline="none",
)


def _inp(id_, val, **kw):
    return dcc.Input(
        id=id_, type="text", value=val, debounce=True,
        style=INPUT_STYLE, **kw,
    )


def _dd(id_, opts, val=None, **kw):
    v = val if val is not None else (
        opts[0]["value"] if opts and isinstance(opts[0], dict) else opts[0]
    )
    return dcc.Dropdown(
        id=id_, options=opts, value=v, clearable=False,
        style={"fontSize": "0.78rem", "marginBottom": "4px"},
        **kw,
    )


def _slider(id_, mn, mx, step, val, marks=None):
    return dcc.Slider(
        id=id_, min=mn, max=mx, step=step, value=val,
        marks=marks or {},
        tooltip={"placement": "bottom", "always_visible": False},
    )


def _graph(id_, h=340):
    return dcc.Graph(
        id=id_,
        config={
            "displayModeBar": "hover",
            "scrollZoom": True,
            "responsive": True,
            "displaylogo": False,
            "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
        },
        style={"height": f"{h}px"},
    )


def _table(id_, h="400px"):
    return dash_table.DataTable(
        id=id_,
        style_table={"overflowX": "auto", "maxHeight": h, "overflowY": "auto"},
        fixed_rows={"headers": True},
        page_size=100,
        sort_action="native",
        filter_action="native",
        style_header={
            "background": "rgba(13,20,40,0.9)",
            "color": "rgba(167,139,250,0.60)",
            "fontFamily": MONO,
            "fontSize": "11px",
            "fontWeight": "500",
            "textTransform": "uppercase",
            "letterSpacing": "0.12em",
            "border": "none",
            "borderBottom": "1px solid rgba(167,139,250,0.10)",
            "padding": "9px 14px",
        },
        style_cell={
            "background": "transparent",
            "color": TEXT,
            "fontFamily": MONO,
            "fontSize": "13px",
            "border": "none",
            "borderBottom": "1px solid rgba(167,139,250,0.05)",
            "padding": "8px 14px",
        },
        style_data_conditional=[
            {
                "if": {"state": "active"},
                "background": "rgba(167,139,250,0.07)",
                "border": "none",
            },
        ],
        style_filter={
            "background": "rgba(11,16,32,0.8)",
            "color": TEXT,
            "fontFamily": MONO,
            "fontSize": "11px",
            "border": "none",
            "borderBottom": "1px solid rgba(167,139,250,0.14)",
        },
    )


# ── Sidebar ───────────────────────────────────────────────────────────────────

def sidebar():
    return html.Div(className="sidebar", children=[

        _head("Database"),
        _label("SQLite path"),
        _inp("db-path", DEFAULT_RUNTIME_DB_PATH),

        _head("Engine"),
        html.Div(id="engine-status-text", className="engine-stopped", children="● stopped"),
        html.Div(id="engine-pid-text", style={
            "fontSize": "0.60rem", "color": "rgba(255,255,255,0.30)",
            "marginBottom": "8px", "wordBreak": "break-all",
            "fontFamily": MONO,
        }),

        _label("Run mode"),
        _dd("engine-mode", [
            {"label": "CSV Replay", "value": "csv"},
            {"label": "Demo (rich)", "value": "demo_rich"},
            {"label": "Demo (console)", "value": "demo_console"},
        ]),
        _label("Replay speed"),
        _dd("replay-speed", [
            {"label": f"{v}×", "value": v}
            for v in [1, 10, 60, 120, 300, 600, 1200, 3600, 7200, 14400]
        ], val=3600),
        _label("History CSV"),
        _inp("history-csv-path", DEFAULT_HISTORY_CSV_PATH),
        html.Div(id="engine-est-runtime", style={
            "fontSize": "0.62rem", "color": "rgba(167,139,250,0.55)",
            "margin": "4px 0", "fontFamily": MONO,
        }),
        html.Div(id="engine-cmd-preview", style={
            "fontSize": "0.55rem", "color": "rgba(167,139,250,0.22)",
            "wordBreak": "break-all", "marginBottom": "10px",
            "lineHeight": "1.6", "fontFamily": MONO,
        }),
        html.Div(style={"display": "flex", "gap": "6px"}, children=[
            html.Button("▶ Start", id="btn-start-engine", n_clicks=0, className="btn btn-primary btn-sm"),
            html.Button("■ Stop",  id="btn-stop-engine",  n_clicks=0, className="btn btn-ghost btn-sm"),
        ]),
        html.Div(id="engine-action-msg"),

        _head("Strategy"),
        _label("YAML path"),
        _inp("strategy-path", DEFAULT_STRATEGY_PATH),

        _head("Display"),
        _label("Refresh (s)"),
        _slider("refresh-sec", 1, 15, 1, 3, {1: "1", 5: "5", 15: "15"}),
        _label("Asset focus"),
        _dd("asset-focus", [
            {"label": "All assets", "value": "all"},
            {"label": "BTC-USD",    "value": "BTC-USD"},
            {"label": "ETH-USD",    "value": "ETH-USD"},
        ]),
        _label("Chart type"),
        _dd("chart-type", [
            {"label": "Line",        "value": "line"},
            {"label": "Candlestick", "value": "candlestick"},
        ]),
        _label("Candle interval"),
        _dd("candle-interval", [
            {"label": v, "value": v} for v in ["1m", "5m", "15m", "1h", "4h", "1d"]
        ], val="5m"),
        _label("Window (ticks)"),
        _slider("last-n-ticks", 50, 2000, 50, 500, {50: "50", 1000: "1k", 2000: "2k"}),

        html.Div(style={"marginTop": "10px"}, children=[
            dcc.Checklist(
                id="display-options",
                options=[
                    {"label": " Trade overlays",  "value": "overlays"},
                    {"label": " Signals only",     "value": "signals_only"},
                    {"label": " Show orders tab",  "value": "show_orders"},
                ],
                value=["overlays", "signals_only", "show_orders"],
                inputStyle={"marginRight": "6px"},
                labelStyle={
                    "display": "block", "margin": "5px 0",
                    "fontSize": "0.75rem", "color": "rgba(255,255,255,0.55)",
                    "cursor": "pointer", "fontFamily": "'DM Sans', sans-serif",
                },
            ),
        ]),

        _head("Filters"),
        _label("Log levels"),
        dcc.Checklist(
            id="event-levels",
            options=[{"label": f" {l}", "value": l} for l in ["info", "warn", "error"]],
            value=["info", "warn"],
            inputStyle={"marginRight": "4px"},
            labelStyle={
                "display": "inline-block", "marginRight": "10px",
                "fontSize": "0.75rem", "color": "rgba(255,255,255,0.50)",
                "cursor": "pointer", "fontFamily": "'DM Sans', sans-serif",
            },
        ),
        _label("Search"),
        _inp("event-search", "", placeholder="filter events…"),
        _label("Max events"),
        _slider("event-limit", 50, 2000, 50, 500, {50: "50", 1000: "1k", 2000: "2k"}),

        _head("Developer"),
        html.Button(
            "Clear All Data", id="btn-clear-data", n_clicks=0,
            className="btn btn-danger btn-sm w-100",
        ),
        html.Button(
            "Confirm Clear", id="btn-confirm-clear", n_clicks=0,
            className="btn btn-danger btn-sm w-100 mt-1",
            style={"display": "none"},
        ),
        html.Div(id="clear-data-msg"),
        html.Div(style={"height": "24px"}),
    ])


# ── Tab contents ──────────────────────────────────────────────────────────────

def tab_overview():
    return html.Div([
        html.Div(id="status-rail"),
        html.Div(className="row2", children=[
            html.Div(className="col-8", children=[
                html.Div(className="card", children=[
                    _card_title("Price Chart"),
                    _graph("price-chart", 330),
                ]),
                html.Div(className="card", children=[
                    _card_title("Equity Curve"),
                    _graph("equity-chart", 180),
                ]),
            ]),
            html.Div(className="col-4", children=[
                html.Div(className="card", style={"height": "calc(100% - 10px)"}, children=[
                    _card_title("Open Positions"),
                    _table("positions-table", "520px"),
                ]),
            ]),
        ]),
    ])


def tab_orders():
    return html.Div([
        html.Div(className="card", children=[
            _card_title("Orders"),
            _table("orders-table"),
        ]),
    ])


def tab_events():
    return html.Div([
        html.Div(className="card", children=[
            _card_title("Event Log"),
            _table("events-table"),
        ]),
    ])


def tab_history():
    return html.Div([
        html.Div(className="card", children=[
            _card_title("History File"),
            html.Div(id="history-summary"),
        ]),
        html.Div(className="card", children=[
            _card_title("Regenerate History"),
            html.Div(className="row2", style={"alignItems": "flex-end", "flexWrap": "wrap"}, children=[
                html.Div(className="col-4", children=[
                    _label("Days back"),
                    _slider("hist-days", 3, 365, 1, 183, {3: "3", 183: "183", 365: "365"}),
                ]),
                html.Div(className="col-2", children=[
                    _label("Granularity"),
                    _dd("hist-granularity", [
                        {"label": "Hourly", "value": "hourly"},
                        {"label": "Daily",  "value": "daily"},
                    ]),
                ]),
                html.Div(className="col-2", children=[
                    _label("Provider"),
                    _dd("hist-provider", [
                        {"label": "Binance",   "value": "binance"},
                        {"label": "CoinGecko", "value": "coingecko"},
                    ]),
                ]),
                html.Div(className="col-3", children=[
                    _label("Output path"),
                    _inp("hist-out-path", DEFAULT_HISTORY_CSV_PATH),
                ]),
                html.Div(style={"display": "flex", "alignItems": "flex-end"}, children=[
                    html.Button("Generate", id="btn-gen-history", n_clicks=0, className="btn btn-primary btn-sm"),
                ]),
            ]),
            html.Div(id="hist-gen-output", style={"marginTop": "12px"}),
        ]),
    ])


def tab_strategy():
    return html.Div([
        html.Div(className="card", children=[html.Div(id="strategy-summary")]),
        html.Div(className="card", children=[
            _card_title("Edit Strategy YAML"),
            dcc.Textarea(
                id="strategy-editor", rows=22,
                style={
                    "width": "100%",
                    "background": "rgba(11,16,32,0.85)",
                    "border": f"1px solid {BORDER_BRIGHT}",
                    "borderRadius": "8px",
                    "color": TEXT,
                    "fontFamily": MONO,
                    "fontSize": "0.72rem",
                    "padding": "10px",
                    "resize": "vertical",
                    "outline": "none",
                    "lineHeight": "1.6",
                },
            ),
            html.Div(style={"display": "flex", "gap": "8px", "marginTop": "12px"}, children=[
                html.Button("Validate", id="btn-validate-strategy", n_clicks=0, className="btn btn-ghost btn-sm"),
                html.Button("Save Strategy", id="btn-save-strategy", n_clicks=0, className="btn btn-primary btn-sm"),
            ]),
            html.Div(id="strategy-action-msg"),
        ]),
    ])


def tab_reports():
    return html.Div([
        html.Div(id="reports-kpi-row"),
        html.Div(className="card", children=[
            html.Div(style={
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "flex-start",
            }, children=[
                html.Div(id="reports-config-display"),
                html.Div(style={
                    "display": "flex", "flexDirection": "column",
                    "alignItems": "flex-end", "gap": "8px",
                }, children=[
                    dcc.Checklist(
                        id="reports-save-snapshot",
                        options=[{"label": " Save snapshot to disk", "value": "save"}],
                        value=["save"],
                        inputStyle={"marginRight": "6px"},
                        labelStyle={
                            "fontSize": "0.68rem",
                            "color": "rgba(255,255,255,0.50)",
                            "fontFamily": "'DM Sans', sans-serif",
                        },
                    ),
                    html.Button(
                        "Build Report", id="btn-build-report", n_clicks=0,
                        className="btn btn-primary btn-sm",
                    ),
                ]),
            ]),
            html.Div(id="reports-build-msg"),
        ]),

        dcc.Tabs(
            id="report-tabs", className="custom-tabs report-tabs",
            value="r-summary",
            children=[
                dcc.Tab(label="Summary", value="r-summary",
                        children=html.Div(id="report-summary-content", style={"paddingTop": "10px"})),
                dcc.Tab(label="Trades",  value="r-trades",
                        children=html.Div(id="report-trades-content",  style={"paddingTop": "10px"})),
                dcc.Tab(label="Equity",  value="r-equity",
                        children=html.Div(id="report-equity-content",  style={"paddingTop": "10px"})),
                dcc.Tab(label="Events",  value="r-events",
                        children=html.Div(id="report-events-content",  style={"paddingTop": "10px"})),
                dcc.Tab(label="Exports", value="r-exports",
                        children=html.Div(id="report-exports-content", style={"paddingTop": "10px"})),
                dcc.Tab(label="Compare", value="r-compare",
                        children=html.Div(id="report-compare-content", style={"paddingTop": "10px"})),
            ],
        ),
    ])


def tab_diagnostics():
    return html.Div([
        html.Div(className="card", children=[
            _card_title("Diagnostics"),
            html.Div(id="diagnostics-content"),
        ]),
    ])


# ── Root layout ───────────────────────────────────────────────────────────────

def build_layout():
    return html.Div([
        dcc.Interval(id="main-interval", interval=3000, n_intervals=0),
        dcc.Store(id="store-report-bundle"),
        dcc.Store(id="store-confirm-clear", data=False),
        dcc.Download(id="download-zip"),

        # ── Navbar ──
        html.Div(className="navbar", children=[
            html.Div(className="navbar-brand", children=[
                html.Span(className="dot"),
                "QUANTUM",
                html.Span(" YOLO ", className="dim"),
                "ENGINE",
            ]),
            html.Div(className="navbar-right", children=[
                html.Div(id="engine-navbar-pill"),
                html.Div(id="navbar-tick-age", className="nav-tick"),
            ]),
        ]),

        # ── Body ──
        html.Div(className="body-wrap", children=[
            sidebar(),
            html.Div(className="main", children=[
                dcc.Tabs(
                    id="main-tabs",
                    className="custom-tabs",
                    value="tab-overview",
                    children=[
                        dcc.Tab(label="Overview",     value="tab-overview",     children=tab_overview()),
                        dcc.Tab(label="Orders",       value="tab-orders",       children=tab_orders()),
                        dcc.Tab(label="Events",       value="tab-events",       children=tab_events()),
                        dcc.Tab(label="History",      value="tab-history",      children=tab_history()),
                        dcc.Tab(label="Strategy",     value="tab-strategy",     children=tab_strategy()),
                        dcc.Tab(label="Reports",      value="tab-reports",      children=tab_reports()),
                        dcc.Tab(label="Diagnostics",  value="tab-diagnostics",  children=tab_diagnostics()),
                    ],
                ),
            ]),
        ]),
    ])