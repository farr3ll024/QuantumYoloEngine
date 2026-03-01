# dashboard/theme.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    # core surfaces
    bg: str = "#0b1220"
    panel: str = "#0f172a"
    panel2: str = "#111c33"
    border: str = "rgba(148,163,184,0.18)"

    # typography
    text: str = "rgba(255,255,255,0.88)"
    text_muted: str = "rgba(255,255,255,0.70)"

    # accents
    primary: str = "#60a5fa"
    success: str = "#34d399"
    warn: str = "#fbbf24"
    danger: str = "#f87171"
    purple: str = "#a78bfa"
    cyan: str = "#22d3ee"
    rose: str = "#fb7185"

    # plotly colorway
    colorway: tuple[str, ...] = (
        "#60a5fa",
        "#a78bfa",
        "#34d399",
        "#fbbf24",
        "#f87171",
        "#22d3ee",
        "#fb7185",
        "#cbd5e1",
    )


THEME = Theme()
