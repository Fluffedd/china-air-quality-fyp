import streamlit as st


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 1.2rem;
        }
        div[data-testid="stMetric"] {
            border: 1px solid rgba(63, 81, 181, 0.18);
            border-radius: 12px;
            padding: 10px 12px;
            background: rgba(248, 250, 255, 0.9);
        }
        div[data-testid="stTabs"] button[role="tab"] {
            border-radius: 8px;
            padding: 8px 12px;
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid rgba(63, 81, 181, 0.18);
            border-radius: 10px;
        }
        .aq-page-hero {
            background: linear-gradient(120deg, #e8f0ff 0%, #f7faff 65%, #eef9f3 100%);
            border: 1px solid rgba(63, 81, 181, 0.15);
            border-radius: 14px;
            padding: 14px 16px;
            margin-bottom: 12px;
        }
        .aq-page-hero h1 {
            margin: 0;
            font-size: 1.45rem;
            color: #1f2a44;
        }
        .aq-page-hero p {
            margin: 6px 0 0 0;
            color: #42526e;
            font-size: 0.95rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(title: str, subtitle: str = "") -> None:
    subtitle_html = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div class="aq-page-hero">
            <h1>{title}</h1>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
