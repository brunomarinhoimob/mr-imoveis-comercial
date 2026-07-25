import html

import streamlit as st


def configure_page(logado: bool = False):
    st.set_page_config(
        page_title="Painel Comercial",
        page_icon="CRM",
        layout="wide" if logado else "centered",
        initial_sidebar_state="expanded" if logado else "collapsed",
    )


def apply_crm_theme():
    st.markdown(
        """
        <style>
        :root {
            --crm-bg: #050816;
            --crm-panel: #0f172a;
            --crm-panel-soft: #111827;
            --crm-border: rgba(148, 163, 184, .22);
            --crm-text: #f8fafc;
            --crm-muted: #94a3b8;
            --crm-blue: #38bdf8;
            --crm-green: #22c55e;
            --crm-red: #ef4444;
            --crm-yellow: #f59e0b;
        }
        .stApp {
            background:
                radial-gradient(circle at 10% 0%, rgba(56, 189, 248, .14), transparent 30rem),
                radial-gradient(circle at 90% 8%, rgba(34, 197, 94, .12), transparent 28rem),
                var(--crm-bg);
            color: var(--crm-text);
        }
        .main .block-container {
            max-width: 1480px;
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #020617 100%);
            border-right: 1px solid var(--crm-border);
        }
        [data-testid="stSidebar"] * {
            color: var(--crm-text) !important;
        }
        h1, h2, h3, h4 {
            color: var(--crm-text);
            letter-spacing: 0;
        }
        p, span, label {
            color: var(--crm-muted);
        }
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        div[data-baseweb="base-input"] {
            background: rgba(15, 23, 42, .95) !important;
            border: 1px solid var(--crm-border) !important;
            border-radius: 10px !important;
        }
        button[kind="primary"], button[data-baseweb="button"] {
            border-radius: 999px;
            border: none;
            background: linear-gradient(135deg, #2563eb, #38bdf8);
            color: #fff;
            font-weight: 700;
            box-shadow: 0 10px 25px rgba(37, 99, 235, .28);
        }
        .crm-hero {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            padding: 1.25rem 1.35rem;
            margin-bottom: 1rem;
            border: 1px solid var(--crm-border);
            border-radius: 18px;
            background:
                linear-gradient(135deg, rgba(37, 99, 235, .18), rgba(34, 197, 94, .08)),
                rgba(15, 23, 42, .88);
            box-shadow: 0 20px 55px rgba(0, 0, 0, .28);
        }
        .crm-kicker {
            color: var(--crm-green);
            font-size: .78rem;
            font-weight: 850;
            text-transform: uppercase;
            letter-spacing: .08em;
            margin-bottom: .35rem;
        }
        .crm-title {
            color: var(--crm-text);
            font-size: 2.1rem;
            font-weight: 850;
            line-height: 1.1;
            margin: 0;
        }
        .crm-subtitle {
            color: var(--crm-muted);
            margin-top: .45rem;
            font-size: .98rem;
        }
        .crm-pill {
            display: inline-flex;
            align-items: center;
            padding: .6rem .9rem;
            border-radius: 999px;
            border: 1px solid rgba(56, 189, 248, .34);
            background: rgba(56, 189, 248, .10);
            color: #bae6fd;
            font-weight: 800;
            white-space: nowrap;
        }
        .crm-card {
            min-height: 116px;
            padding: 1rem 1.05rem;
            border-radius: 16px;
            border: 1px solid var(--crm-border);
            background:
                linear-gradient(180deg, rgba(255,255,255,.045), rgba(255,255,255,.015)),
                rgba(17, 24, 39, .88);
            box-shadow: 0 14px 34px rgba(0, 0, 0, .22);
        }
        .crm-card-label {
            color: #cbd5e1;
            font-size: .80rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: .04em;
            min-height: 2rem;
        }
        .crm-card-value {
            color: var(--crm-text);
            font-size: 2.05rem;
            line-height: 1;
            font-weight: 850;
            margin-top: .4rem;
        }
        .crm-card-accent {
            width: 40px;
            height: 4px;
            border-radius: 999px;
            margin-top: .9rem;
            background: linear-gradient(90deg, var(--crm-green), var(--crm-blue));
        }
        .crm-section {
            margin: 1.35rem 0 .85rem;
        }
        .crm-section h2 {
            margin: 0;
            font-size: 1.35rem;
            font-weight: 850;
        }
        .crm-section p {
            margin: .25rem 0 0;
            color: var(--crm-muted);
            font-size: .9rem;
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid var(--crm-border);
            border-radius: 14px;
            overflow: hidden;
            background: rgba(15, 23, 42, .72);
        }
        .stAlert {
            border-radius: 14px;
        }
        footer {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def safe_text(value) -> str:
    return html.escape(str(value or ""))


def hero(title: str, subtitle: str, pill: str = ""):
    st.markdown(
        f"""
        <div class="crm-hero">
            <div>
                <div class="crm-kicker">Dashboard Comercial</div>
                <h1 class="crm-title">{safe_text(title)}</h1>
                <div class="crm-subtitle">{safe_text(subtitle)}</div>
            </div>
            <div class="crm-pill">{safe_text(pill)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(title: str, subtitle: str = ""):
    st.markdown(
        f"""
        <div class="crm-section">
            <h2>{safe_text(title)}</h2>
            <p>{safe_text(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def format_number(value) -> str:
    try:
        number = int(value)
    except Exception:
        number = 0
    return f"{number:,}".replace(",", ".")


def format_currency(value) -> str:
    try:
        number = float(value)
    except Exception:
        number = 0.0
    return f"R$ {number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def metric_card(label: str, value, currency: bool = False):
    display = format_currency(value) if currency else format_number(value)
    st.markdown(
        f"""
        <div class="crm-card">
            <div class="crm-card-label">{safe_text(label)}</div>
            <div class="crm-card-value">{safe_text(display)}</div>
            <div class="crm-card-accent"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_grid(items: list[tuple[str, object]], columns: int = 4, currency_labels: set[str] | None = None):
    currency_labels = currency_labels or set()
    cols = st.columns(columns)
    for idx, (label, value) in enumerate(items):
        with cols[idx % columns]:
            metric_card(label, value, currency=label in currency_labels)
