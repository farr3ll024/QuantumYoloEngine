# dashboard/theme.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    # surfaces (lighter purple, still dark enough for contrast)
    bg: str = "#120A2A"  # page + header background
    panel: str = "#160D33"  # card/panel background
    panel2: str = "#110826"  # deeper card gradient
    border: str = "rgba(255,255,255,0.00)"  # no borders

    # typography
    text: str = "rgba(255,255,255,0.92)"
    text_muted: str = "rgba(255,255,255,0.70)"

    # brand + accents (purple-led)
    primary: str = "#a78bfa"
    primary_2: str = "#c4b5fd"
    cyan: str = "#22d3ee"
    success: str = "#34d399"
    warn: str = "#fbbf24"
    danger: str = "#fb7185"
    blue: str = "#60a5fa"
    slate: str = "#cbd5e1"

    # plotly colorway
    colorway: tuple[str, ...] = (
        "#a78bfa",
        "#c4b5fd",
        "#22d3ee",
        "#60a5fa",
        "#34d399",
        "#fbbf24",
        "#fb7185",
        "#cbd5e1",
    )


THEME = Theme()
