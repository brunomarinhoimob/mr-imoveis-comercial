import streamlit as st
import pandas as pd
import altair as alt
from streamlit_autorefresh import st_autorefresh

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="Produção Comercial",
    page_icon="📞",
    layout="wide"
)

st_autorefresh(interval=30 * 1000, key="auto_refresh_producao")

# =========================================================
# CSS
# =========================================================
st.markdown("""
<style>

.stApp {
    background: #020617;
}

div[data-testid="stMetric"] {
    background: linear-gradient(145deg, #0f172a 0%, #020617 100%);
    border: 1px solid rgba(148,163,184,0.20);
    padding: 18px;
    border-radius: 18px;
}

div[data-testid="stMetricLabel"] {
    color: #94a3b8;
}

div[data-testid="stMetricValue"] {
    color: white;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# GOOGLE SHEETS
# =========================================================
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID = "1161609337"

CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

# =========================================================
# CARREGAR DADOS
# =========================================================
@st.cache_data(ttl=60)
def carregar_base():
    df = pd.read_csv(CSV_URL)

    df.columns = [c.strip().upper() for c in df.columns]

    if "DATA" not in df.columns:
        df["DATA"] = pd.NaT
    else:
        df["DATA"] = pd.to_datetime(
            df["DATA"],
            dayfirst=True,
            errors="coerce"
        )

    colunas_numericas = [
        "ATENDEU",
        "WHATSAPP ENVIADO",
        "CONTATO INVÁLIDO",
        "TOTAL"
    ]

    for col in colunas_numericas:
        if col not in df.columns:
            df[col] = 0
        else:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            ).fillna(0)

    return df

df = carregar_base()

# =========================================================
# TÍTULO
# =========================================================
st.title("📞 Produção Comercial")

st.caption(
    "Controle operacional diário de prospecção comercial"
)

# =========================================================
# VALIDAÇÃO
# =========================================================
if df.empty:
    st.warning("Sem dados na aba PRODUÇÃO_COMERCIAL.")
    st.stop()

# =========================================================
# FILTRO DATA
# =========================================================
df["DATA"] = pd.to_datetime(
    df["DATA"],
    dayfirst=True,
    errors="coerce"
)

df = df[df["DATA"].notna()].copy()

if df.empty:
    st.warning("Nenhuma data válida encontrada na aba PRODUÇÃO_COMERCIAL.")
    st.stop()

data_min = df["DATA"].min().date()
data_max = df["DATA"].max().date()

periodo = st.sidebar.date_input(
    "Período",
    value=(data_min, data_max),
    min_value=data_min,
    max_value=data_max
)

if isinstance(periodo, tuple):
    data_ini, data_fim = periodo
else:
    data_ini = periodo
    data_fim = periodo

df = df[
    (df["DATA"].dt.date >= data_ini) &
    (df["DATA"].dt.date <= data_fim)
].copy()

if df.empty:
    st.info("Nenhuma produção encontrada no período selecionado.")
    st.stop()

# =========================================================
# RECALCULA TOTAL SE NECESSÁRIO
# =========================================================
df["TOTAL_CALCULADO"] = (
    df["ATENDEU"] +
    df["WHATSAPP ENVIADO"] +
    df["CONTATO INVÁLIDO"]
)

df["TOTAL"] = df["TOTAL"].fillna(0)

df.loc[df["TOTAL"] == 0, "TOTAL"] = df.loc[
    df["TOTAL"] == 0,
    "TOTAL_CALCULADO"
]

# =========================================================
# KPIs
# =========================================================
total_atendeu = int(df["ATENDEU"].sum())
total_whatsapp = int(df["WHATSAPP ENVIADO"].sum())
total_invalido = int(df["CONTATO INVÁLIDO"].sum())
total_operacional = int(df["TOTAL"].sum())

taxa_atendimento = (
    (total_atendeu / total_operacional) * 100
    if total_operacional > 0 else 0
)

# =========================================================
# CARDS
# =========================================================
c1, c2, c3, c4, c5 = st.columns(5)

c1.metric(
    "📞 Total Operacional",
    total_operacional
)

c2.metric(
    "✅ Atendeu",
    total_atendeu
)

c3.metric(
    "💬 WhatsApp",
    total_whatsapp
)

c4.metric(
    "🚫 Contato Inválido",
    total_invalido
)

c5.metric(
    "📊 Taxa Atendimento",
    f"{taxa_atendimento:.1f}%"
)

# =========================================================
# GRÁFICO
# =========================================================
st.markdown("---")
st.subheader("📈 Evolução diária")

df_chart = df.copy()

chart = (
    alt.Chart(df_chart)
    .transform_fold(
        [
            "ATENDEU",
            "WHATSAPP ENVIADO",
            "CONTATO INVÁLIDO"
        ],
        as_=["Tipo", "Quantidade"]
    )
    .mark_line(point=True)
    .encode(
        x=alt.X("DATA:T", title="Data"),
        y=alt.Y("Quantidade:Q", title="Quantidade"),
        color=alt.Color("Tipo:N", title="Tipo")
    )
    .properties(height=420)
)

st.altair_chart(
    chart,
    use_container_width=True
)

# =========================================================
# TABELA
# =========================================================
st.markdown("---")
st.subheader("📋 Produção detalhada")

df_exibir = df.copy()

df_exibir["DATA"] = df_exibir["DATA"].dt.strftime("%d/%m/%Y")

colunas_exibir = [
    "DATA",
    "ATENDEU",
    "WHATSAPP ENVIADO",
    "CONTATO INVÁLIDO",
    "TOTAL"
]

st.dataframe(
    df_exibir[colunas_exibir],
    use_container_width=True,
    hide_index=True
)

# =========================================================
# MÉDIA DIÁRIA
# =========================================================
st.markdown("---")
st.subheader("📌 Média diária")

dias = df["DATA"].dt.date.nunique()

media_total = total_operacional / dias if dias > 0 else 0
media_atendeu = total_atendeu / dias if dias > 0 else 0
media_whats = total_whatsapp / dias if dias > 0 else 0

m1, m2, m3 = st.columns(3)

m1.metric(
    "Média Operacional",
    f"{media_total:.1f}"
)

m2.metric(
    "Média Atendeu",
    f"{media_atendeu:.1f}"
)

m3.metric(
    "Média WhatsApp",
    f"{media_whats:.1f}"
)