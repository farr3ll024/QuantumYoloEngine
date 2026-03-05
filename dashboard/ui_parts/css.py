from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from ..theme import THEME


def inject_scroll_lock() -> None:
    """
    Injects a JS snippet via st.components.v1.html (which actually executes JS,
    unlike st.markdown which strips <script> tags).

    Fixes the confirmed Streamlit bug (issue #11971) where st.fragment(run_every=...)
    resets scroll to top on every fragment rerun.

    The script:
    1. Listens for scroll events and saves window.scrollY into a closure variable
    2. Uses a MutationObserver on the Streamlit root div to detect rerenders
    3. After each rerender, instantly restores the saved scroll position
    """
    components.html(
        """
        <script>
        (function() {
            // Target the parent Streamlit window, not this iframe
            var win = window.parent;
            var doc = win.document;

            if (win.__scrollLockInstalled) return;
            win.__scrollLockInstalled = true;

            var savedY = 0;

            win.addEventListener('scroll', function() {
                savedY = win.scrollY;
            }, { passive: true });

            var observer = new MutationObserver(function() {
                if (savedY > 10) {
                    win.scrollTo({ top: savedY, behavior: 'instant' });
                }
            });

            function attachObserver() {
                var root = doc.getElementById('root');
                if (root) {
                    // Observe only direct children of root to minimise callback frequency
                    observer.observe(root, { childList: true, subtree: false });
                } else {
                    setTimeout(attachObserver, 100);
                }
            }
            attachObserver();
        })();
        </script>
        """,
        height=0,
        scrolling=False,
    )


def inject_global_css() -> None:
    inject_scroll_lock()
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
