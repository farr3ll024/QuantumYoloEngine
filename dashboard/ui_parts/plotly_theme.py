from __future__ import annotations

import plotly.graph_objects as go

from ..theme import THEME

PLOTLY_CONFIG = {
    "displayModeBar": True,
    "scrollZoom": True,
    "responsive": True,
}


def apply_dark_plotly_theme(fig: go.Figure) -> None:
    fig.update_layout(
        paper_bgcolor=THEME.bg,
        plot_bgcolor=THEME.bg,
        font=dict(color=THEME.text),
        legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0, font=dict(color=THEME.text_muted)),
        margin=dict(l=60, r=20, t=40, b=60),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="rgba(14,6,32,0.96)", font=dict(color="white")),
        colorway=list(THEME.colorway),
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor="rgba(255,255,255,0.10)",
        zeroline=False,
        tickfont=dict(color=THEME.text_muted, size=11),
        title=dict(font=dict(color=THEME.text, size=12)),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(255,255,255,0.10)",
        zeroline=False,
        tickfont=dict(color=THEME.text_muted, size=11),
        title=dict(font=dict(color=THEME.text, size=12)),
    )