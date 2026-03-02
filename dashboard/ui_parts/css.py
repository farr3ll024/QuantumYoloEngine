from __future__ import annotations

import streamlit as st

from ..theme import THEME


def inject_global_css() -> None:
    st.markdown(
        f"""
        <style>
          html, body, [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] > .main {{
            background: {THEME.bg} !important;
          }}

          header[data-testid="stHeader"] {{
            background: {THEME.bg} !important;
            border-bottom: 1px solid rgba(167,139,250,0.10) !important;
          }}
          [data-testid="stToolbar"] {{
            background: {THEME.bg} !important;
          }}
          [data-testid="stDecoration"] {{
            background: {THEME.bg} !important;
          }}

          section[data-testid="stSidebar"] > div {{
            background: {THEME.panel} !important;
          }}

          .block-container {{
            padding-top: 2.0rem;
            padding-bottom: 2.25rem;
            max-width: 1440px;
          }}

          h1, h2, h3 {{
            letter-spacing: -0.02em;
          }}
          h1 {{
            margin-bottom: 0.15rem;
          }}

          div[data-testid="stVerticalBlockBorderWrapper"] {{
            border: none !important;
            border-radius: 18px !important;
            background:
              radial-gradient(1200px 600px at 20% 0%, rgba(167,139,250,0.14) 0%, rgba(0,0,0,0) 60%),
              linear-gradient(180deg, {THEME.panel} 0%, {THEME.panel2} 100%) !important;
            box-shadow:
              0 18px 45px rgba(0,0,0,0.38),
              0 0 0 1px rgba(0,0,0,0.00) inset !important;
          }}

          hr {{
            border-color: rgba(167,139,250,0.10) !important;
          }}

          button[role="tab"] {{
            border-radius: 10px !important;
            padding: 0.30rem 0.80rem !important;
            margin-right: 0.25rem !important;
          }}
          button[role="tab"][aria-selected="true"] {{
            border: none !important;
            box-shadow: none !important;
          }}
          button[role="tab"][aria-selected="true"]::after {{
            content: "";
            display: block;
            height: 3px;
            border-radius: 999px;
            margin-top: 6px;
            background: rgba(167,139,250,0.88);
          }}

          div[data-testid="stDataFrame"] {{
            border-radius: 14px;
            overflow: hidden;
            border: none !important;
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )