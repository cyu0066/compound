"""
Look and feel shared by every page: fonts, spacing, and chart styling.

Body text is Times New Roman (falling back to Times / Liberation Serif /
generic serif on machines without it). Headings, metrics and navigation use
Montserrat, loaded from Google Fonts. Change BODY_FONT or HEADING_FONT here to
restyle the whole app.
"""
import streamlit as st

BODY_FONT = '"Times New Roman", Times, "Liberation Serif", serif'
HEADING_FONT = '"Montserrat", "Helvetica Neue", Arial, sans-serif'

ACCENT = "#2F6B5A"
PALETTE = ["#2F6B5A", "#C08A3E", "#4A6FA5", "#B5523B", "#7A6C9D", "#8AA29E"]
GRID = "#E4DFD3"
INK = "#1F2328"

DISCLAIMER = (
    "Compound is a personal tracking tool, not financial advice. Projections depend on the return and "
    "volatility you assume, and rebalancing suggestions ignore tax and trading costs."
)

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600;700&display=swap');

/* Bigger type everywhere: most Streamlit sizes are in rem, so this scales them all. */
html {{ font-size: 19px; }}

/* Body text */
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea,
.stApp button, .stApp [data-baseweb="select"], .stApp [data-testid="stCaptionContainer"],
.stApp [data-testid="stMarkdownContainer"], .stApp [data-testid="stAlertContainer"] {{
    font-family: {BODY_FONT} !important;
}}
.stApp p, .stApp li, .stApp label {{ font-size: 1.08rem; line-height: 1.6; }}
.stApp [data-testid="stCaptionContainer"] {{ font-size: 0.98rem; line-height: 1.55; }}

/* Headings, metrics and navigation */
.stApp h1, .stApp h2, .stApp h3, .stApp h4,
.stApp [data-testid="stMetricLabel"] p, .stApp [data-testid="stMetricValue"],
.stApp [data-testid="stTabs"] button p,
.stApp header a, .stApp [data-testid*="NavLink"], .stApp [data-testid*="stSidebarNav"] a {{
    font-family: {HEADING_FONT} !important;
    letter-spacing: -0.01em;
}}
.stApp h1 {{ font-size: 2.3rem; font-weight: 600; padding: 0.4rem 0 0.2rem; letter-spacing: -0.02em; }}
.stApp h2 {{ font-size: 1.15rem; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; padding: 0; }}
.stApp h3 {{ font-size: 1.3rem; font-weight: 600; padding-top: 0.2rem; }}

/* Sections: a hairline above each, with generous space either side */
[data-testid="stHeading"]:has(h2) {{
    border-top: 1px solid {GRID};
    margin-top: 2.75rem;
    padding-top: 1.6rem;
}}
/* ...and one under the page title block */
.page-rule {{ border: 0; border-top: 1px solid {GRID}; margin: 0; }}
[data-testid="stHeading"]:has(h2) {{ padding-bottom: 0.4rem; }}
/* the page rule already divides the first section from the title */
[data-testid="stElementContainer"]:has(.page-rule) + [data-testid="stElementContainer"] [data-testid="stHeading"]:has(h2),
[data-testid="stElementContainer"]:has(.page-rule) + [data-testid="stHeading"]:has(h2) {{
    border-top: 0 !important; margin-top: 0 !important; padding-top: 0.2rem !important;
}}
[data-testid="stExpander"] details {{ border-radius: 4px; }}

/* Roomier layout: a readable column with generous space between sections */
[data-testid="stMainBlockContainer"], .block-container {{
    max-width: 1100px;
    padding: 3.5rem 2.5rem 6rem;
}}
[data-testid="stVerticalBlock"] {{ gap: 1.5rem; }}
[data-testid="stHorizontalBlock"] {{ gap: 1.5rem; }}

/* Cards */
[data-testid="stVerticalBlockBorderWrapper"] {{
    border-radius: 4px;
    padding: 0.8rem 1rem;
    background: #FFFFFF;
}}

/* Metrics: the number sits inside a markdown paragraph, so override the body-text rules */
.stApp [data-testid="stMetricLabel"] p {{ font-size: 0.72rem; font-weight: 500; letter-spacing: 0.08em; text-transform: uppercase; color: #6b7076; }}
.stApp [data-testid="stMetricValue"], .stApp [data-testid="stMetricValue"] p,
.stApp [data-testid="stMetricValue"] [data-testid="stMarkdownContainer"] {{
    font-family: {HEADING_FONT} !important;
    font-size: 1.7rem !important;
    font-weight: 500;
    line-height: 1.25;
}}

/* Top navigation labels */
.stApp [data-testid="stTopNavLink"],
.stApp [data-testid="stTopNavLink"] [data-testid="stMarkdownContainer"],
.stApp [data-testid="stTopNavLink"] [data-testid="stMarkdownContainer"] p {{
    font-family: {HEADING_FONT} !important;
    font-size: 0.85rem;
    line-height: 1.4;
}}

/* Buttons and inputs */
.stApp button {{ border-radius: 3px; padding: 0.35rem 1.1rem; box-shadow: none; }}
.stApp [data-testid="stExpander"] {{ border-radius: 4px; }}
.stApp [data-baseweb="input"], .stApp [data-baseweb="select"] > div {{ border-radius: 3px; }}
.stApp [data-testid="stAlertContainer"] {{ border-radius: 3px; }}
</style>
"""


def apply_theme() -> None:
    """Inject the fonts and spacing. Call once per run, from the entry script."""
    st.markdown(_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str | None = None) -> None:
    st.title(title)
    if subtitle:
        st.caption(subtitle)
    st.markdown('<hr class="page-rule">', unsafe_allow_html=True)


def money(value: float, cents: bool = True) -> str:
    return f"${value:,.2f}" if cents else f"${value:,.0f}"


def compact_money(value: float) -> str:
    """$950, $44.7k, $1.2M — for tight spaces."""
    sign = "-" if value < 0 else ""
    v = abs(value)
    if v >= 1_000_000:
        return f"{sign}${v / 1_000_000:.1f}M"
    if v >= 10_000:
        return f"{sign}${v / 1_000:.1f}k"
    return f"{sign}${v:,.0f}"


def years_label(years: float) -> str:
    """'1 year' / '6 years' / '1.5 years'."""
    return "1 year" if years == 1 else f"{years:g} years"


def style_figure(fig, height: int = 380):
    """Apply the app's fonts, colours and spacing to a Plotly figure."""
    fig.update_layout(
        font=dict(family=BODY_FONT, size=15, color=INK),
        colorway=PALETTE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=30, b=30, l=10, r=10),
        height=height,
        legend=dict(orientation="h", yanchor="top", y=-0.18, x=0),
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID)
    return fig
