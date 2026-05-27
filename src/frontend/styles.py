import streamlit as st

from frontend.config import BTG_BLUE, INK, LINE, MUTED, SURFACE


def configure_page() -> None:
    st.set_page_config(
        page_title="BTG | FII Intelligence",
        page_icon="BTG",
        layout="wide",
    )


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
        :root {{
            --btg-blue: {BTG_BLUE};
            --ink: {INK};
            --muted: {MUTED};
            --line: {LINE};
            --surface: {SURFACE};
        }}
        .block-container {{
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 1420px;
        }}
        h1, h2, h3 {{
            color: var(--ink);
            letter-spacing: 0;
        }}
        .top-band {{
            border: 1px solid var(--line);
            border-left: 6px solid var(--btg-blue);
            background: linear-gradient(90deg, #FFFFFF 0%, #F4F8FC 100%);
            padding: 18px 20px;
            border-radius: 8px;
            margin-bottom: 14px;
        }}
        .top-title {{
            font-size: 28px;
            line-height: 1.15;
            font-weight: 760;
            color: var(--ink);
            margin: 0;
        }}
        .top-subtitle {{
            color: var(--muted);
            font-size: 15px;
            margin-top: 6px;
            max-width: 980px;
        }}
        .section-note {{
            color: var(--muted);
            font-size: 14px;
            margin: -6px 0 16px 0;
        }}
        .status-pill {{
            display: inline-block;
            border: 1px solid var(--line);
            border-radius: 999px;
            padding: 4px 10px;
            font-size: 12px;
            font-weight: 680;
            background: #FFFFFF;
            color: var(--ink);
            margin-right: 6px;
            margin-bottom: 6px;
        }}
        .status-ok {{
            border-color: #B7E4D4;
            background: #EAF8F3;
            color: #06664D;
        }}
        .status-mid {{
            border-color: #F4D48A;
            background: #FFF7E3;
            color: #7A4B00;
        }}
        .status-empty {{
            border-color: #F3B3BB;
            background: #FFF1F3;
            color: #912B38;
        }}
        .play-step {{
            border: 1px solid var(--line);
            background: #FFFFFF;
            border-radius: 8px;
            padding: 12px 14px;
            min-height: 104px;
        }}
        .play-step-number {{
            width: 26px;
            height: 26px;
            border-radius: 50%;
            background: var(--btg-blue);
            color: #FFFFFF;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 13px;
            font-weight: 760;
            margin-right: 8px;
        }}
        .play-step-title {{
            font-weight: 760;
            color: var(--ink);
        }}
        .play-step-text {{
            color: var(--muted);
            font-size: 13px;
            margin-top: 8px;
        }}
        div[data-testid="stMetric"] {{
            background: #FFFFFF;
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 12px;
        }}
        div[data-testid="stMetricValue"] {{
            color: var(--ink);
            font-size: 24px;
        }}
        .coverage-track {{
            height: 10px;
            width: 100%;
            border-radius: 999px;
            background: #E9EEF5;
            overflow: hidden;
            border: 1px solid #D8E0EA;
        }}
        .coverage-fill {{
            height: 100%;
            border-radius: 999px;
        }}
        .small-muted {{
            color: var(--muted);
            font-size: 12px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
