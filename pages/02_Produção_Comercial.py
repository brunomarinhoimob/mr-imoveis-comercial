import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
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

GID_PRODUCAO = "1161609337"
GID_PROCESSOS = "1574157905"

CSV_PRODUCAO = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_PRODUCAO}"
CSV_PROCESSOS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_PROCESSOS}"

# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================
def mes_ano_ptbr_para_date(valor):
    if pd.isna(valor):
        return pd.NaT

    s = str(valor).strip().lower()
    if not s:
        return pd.NaT

    meses = {
        "janeiro": 1,
        "fevereiro": 2,
        "março": 3,
        "marco": 3,
        "abril": 4,
        "maio": 5,
        "junho": 6,
        "julho": 7,
        "agosto": 8,
        "setembro": 9,
        "outubro": 10,
        "novembro": 11,
        "dezembro": 12,
    }

    try:
        partes = s.split()
        mes_txt = partes[0]
        ano = int(partes[-1])
        mes_num = meses.get(mes_txt)

        if mes_num is None:
            return pd.NaT

        return datetime(ano, mes_num, 1).date()

    except Exception:
        return pd.NaT


def tratar_data_base(df):
    possiveis_cols_base = [
        "DATA BASE",
        "DATA_BASE",
        "DT BASE",
        "DATA REF",
        "DATA REFERÊNCIA",
        "DATA REFERENCIA",
    ]

    col_data_base = next((c for c in possiveis_cols_base if c in df.columns), None)

    if col_data_base:
        base_raw = df[col_data_base].fillna("").astype(str).str.strip()
        df["DATA_BASE_LABEL"] = base_raw.str.lower().str.title()
        df["DATA_BASE"] = base_raw.apply(mes_ano_ptbr_para_date)
    else:
        df["DATA_BASE_LABEL"] = ""
        df["DATA_BASE"] = pd.NaT

    return df


# =========================================================
# CARREGAR PRODUÇÃO COMERCIAL
# =========================================================
@st.cache_data(ttl=60)
def carregar_base():
    df = pd.read_csv(CSV_PRODUCAO)

    df.columns = [c.strip().upper() for c in df.columns]

    if "DATA" not in df.columns:
        df["DATA"] = pd.NaT
    else:
        df["DATA"] = pd.to_datetime(
            df["DATA"],
            dayfirst=True,
            errors="coerce"
        )

    df = tratar_data_base(df)

    colunas_numericas = [
        "ATENDEU",
        "PROSPECT",
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


# =========================================================
# CARREGAR CONTROLE DE PROCESSOS
# =========================================================
@st.cache_data(ttl=60)
def carregar_processos():
    dfp = pd.read_csv(CSV_PROCESSOS)

    dfp.columns = [c.strip().upper() for c in dfp.columns]

    if "DATA" in dfp.columns:
        dfp["DATA"] = pd.to_datetime(
            dfp["DATA"],
            dayfirst=True,
            errors="coerce"
        )
    elif "DIA" in dfp.columns:
        dfp["DATA"] = pd.to_datetime(
            dfp["DIA"],
            dayfirst=True,
            errors="coerce"
        )
    else:
        dfp["DATA"] = pd.NaT

    dfp = tratar_data_base(dfp)

    possiveis_status = [
        "SITUAÇÃO",
        "SITUAÇÃO ATUAL",
        "STATUS",
        "SITUACAO",
        "SITUACAO ATUAL",
    ]

    col_status = next((c for c in possiveis_status if c in dfp.columns), None)

    if col_status:
        dfp["STATUS_ORIGINAL"] = (
            dfp[col_status]
            .fillna("")
            .astype(str)
            .str.upper()
            .str.strip()
        )
    else:
        dfp["STATUS_ORIGINAL"] = ""

    dfp["STATUS_BASE"] = ""

    s = dfp["STATUS_ORIGINAL"]

    dfp.loc[s.str.contains("EM ANÁLISE", na=False), "STATUS_BASE"] = "EM ANÁLISE"
    dfp.loc[s.str.contains("REANÁLISE", na=False), "STATUS_BASE"] = "REANÁLISE"

    dfp.loc[s.str.strip() == "APROVAÇÃO", "STATUS_BASE"] = "APROVADO"
    dfp.loc[s.str.contains("APROVADO BACEN", na=False), "STATUS_BASE"] = "APROVADO BACEN"
    dfp.loc[s.str.contains("APROVADO COM RESTRIÇÃO", na=False), "STATUS_BASE"] = "APROVADO COM RESTRIÇÃO"

    dfp.loc[s.str.contains("REPROV", na=False), "STATUS_BASE"] = "REPROVADO"
    dfp.loc[s.str.contains("VENDA GERADA", na=False), "STATUS_BASE"] = "VENDA GERADA"
    dfp.loc[s.str.contains("VENDA INFORMADA", na=False), "STATUS_BASE"] = "VENDA INFORMADA"
    dfp.loc[s.str.contains("DESIST", na=False), "STATUS_BASE"] = "DESISTIU"

    possiveis_nome = ["NOME", "CLIENTE", "NOME CLIENTE", "NOME DO CLIENTE", "NOME_CLIENTE_BASE"]
    possiveis_cpf = ["CPF", "CPF CLIENTE", "CPF DO CLIENTE", "CPF_CLIENTE_BASE"]

    col_nome = next((c for c in possiveis_nome if c in dfp.columns), None)
    col_cpf = next((c for c in possiveis_cpf if c in dfp.columns), None)

    if col_nome:
        dfp["NOME_CLIENTE_BASE"] = (
            dfp[col_nome]
            .fillna("NÃO INFORMADO")
            .astype(str)
            .str.upper()
            .str.strip()
        )
    else:
        dfp["NOME_CLIENTE_BASE"] = "NÃO INFORMADO"

    if col_cpf:
        dfp["CPF_CLIENTE_BASE"] = (
            dfp[col_cpf]
            .fillna("")
            .astype(str)
            .str.replace(r"\D", "", regex=True)
        )
    else:
        dfp["CPF_CLIENTE_BASE"] = ""

    dfp["CHAVE_CLIENTE"] = (
        dfp["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO")
        + " | "
        + dfp["CPF_CLIENTE_BASE"].fillna("")
    )

    return dfp


df = carregar_base()
df_processos = carregar_processos()

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
# LIMPA DATAS VÁLIDAS
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

# =========================================================
# FILTROS: DATA OU DATA BASE
# =========================================================
st.sidebar.title("Filtros 🔎")

modo_periodo = st.sidebar.radio(
    "Modo de filtro",
    ["Por DATA BASE", "Por DATA"],
    index=0
)

data_ini = None
data_fim = None
data_base_sel = None

if modo_periodo == "Por DATA BASE":
    bases_df = (
        df[["DATA_BASE", "DATA_BASE_LABEL"]]
        .dropna(subset=["DATA_BASE"])
        .drop_duplicates()
        .sort_values("DATA_BASE")
    )

    if bases_df.empty:
        st.warning("Nenhuma DATA BASE válida encontrada na aba PRODUÇÃO_COMERCIAL.")
        st.stop()

    opcoes_base = bases_df["DATA_BASE_LABEL"].tolist()
    ultima_base = opcoes_base[-1]

    data_base_sel = st.sidebar.selectbox(
        "DATA BASE",
        options=opcoes_base,
        index=opcoes_base.index(ultima_base)
    )

    df = df[df["DATA_BASE_LABEL"] == data_base_sel].copy()

    if df.empty:
        st.info("Nenhuma produção encontrada para essa DATA BASE.")
        st.stop()

    data_ini = df["DATA"].min().date()
    data_fim = df["DATA"].max().date()

else:
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
# FILTRA CONTROLE DE PROCESSOS NO MESMO PERÍODO / DATA BASE
# =========================================================
df_processos["DATA"] = pd.to_datetime(
    df_processos["DATA"],
    dayfirst=True,
    errors="coerce"
)

df_processos = df_processos[df_processos["DATA"].notna()].copy()

if modo_periodo == "Por DATA BASE":
    df_processos_periodo = df_processos[
        df_processos["DATA_BASE_LABEL"] == data_base_sel
    ].copy()
else:
    df_processos_periodo = df_processos[
        (df_processos["DATA"].dt.date >= data_ini) &
        (df_processos["DATA"].dt.date <= data_fim)
    ].copy()

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
# KPIs PRODUÇÃO
# =========================================================
total_atendeu = int(df["ATENDEU"].sum())
total_prospect = int(df["PROSPECT"].sum())
total_whatsapp = int(df["WHATSAPP ENVIADO"].sum())
total_invalido = int(df["CONTATO INVÁLIDO"].sum())
total_operacional = int(df["TOTAL"].sum())

taxa_atendimento = (
    (total_atendeu / total_operacional) * 100
    if total_operacional > 0 else 0
)

taxa_prospect = (
    (total_prospect / total_operacional) * 100
    if total_operacional > 0 else 0
)

# =========================================================
# KPIs PROCESSOS
# =========================================================
analises = int(
    df_processos_periodo["STATUS_BASE"]
    .isin(["EM ANÁLISE", "REANÁLISE"])
    .sum()
)

aprovacoes = int(
    df_processos_periodo["STATUS_BASE"]
    .isin(["APROVADO", "APROVADO BACEN", "APROVADO COM RESTRIÇÃO"])
    .sum()
)

vendas = int(
    df_processos_periodo[
        df_processos_periodo["STATUS_BASE"].isin(["VENDA GERADA", "VENDA INFORMADA"])
    ]["CHAVE_CLIENTE"]
    .nunique()
)

conv_atendeu_total = (
    (total_atendeu / total_operacional) * 100
    if total_operacional > 0 else 0
)

conv_prospect_atendeu = (
    (total_prospect / total_atendeu) * 100
    if total_atendeu > 0 else 0
)

conv_analise_total = (
    (analises / total_operacional) * 100
    if total_operacional > 0 else 0
)

conv_analise_prospect = (
    (analises / total_prospect) * 100
    if total_prospect > 0 else 0
)

conv_aprov_analise = (
    (aprovacoes / analises) * 100
    if analises > 0 else 0
)

conv_venda_analise = (
    (vendas / analises) * 100
    if analises > 0 else 0
)

contatos_por_analise = (
    total_operacional / analises
    if analises > 0 else 0
)

contatos_por_venda = (
    total_operacional / vendas
    if vendas > 0 else 0
)

# =========================================================
# CARDS
# =========================================================
c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric(
    "📞 Total Operacional",
    total_operacional
)

c2.metric(
    "✅ Atendeu",
    total_atendeu
)

c3.metric(
    "🔥 Prospect",
    total_prospect
)

c4.metric(
    "💬 WhatsApp",
    total_whatsapp
)

c5.metric(
    "🚫 Contato Inválido",
    total_invalido
)

c6.metric(
    "📊 Taxa Prospect",
    f"{taxa_prospect:.1f}%"
)

# =========================================================
# CARDS DE RESULTADO
# =========================================================
st.markdown("---")
st.subheader("🎯 Resultado gerado no período")

r1, r2, r3 = st.columns(3)

r1.metric(
    "📄 Análises",
    analises
)

r2.metric(
    "✅ Aprovações",
    aprovacoes
)

r3.metric(
    "💰 Vendas",
    vendas
)

# =========================================================
# CARDS DE CONVERSÃO
# =========================================================
st.markdown("---")
st.subheader("📊 Conversões da Produção Comercial")

v1, v2, v3, v4 = st.columns(4)

v1.metric(
    "Atendeu / Total",
    f"{conv_atendeu_total:.1f}%"
)

v2.metric(
    "Prospect / Atendeu",
    f"{conv_prospect_atendeu:.1f}%"
)

v3.metric(
    "Análise / Total",
    f"{conv_analise_total:.1f}%"
)

v4.metric(
    "Análise / Prospect",
    f"{conv_analise_prospect:.1f}%"
)

v5, v6, v7, v8 = st.columns(4)

v5.metric(
    "Aprovação / Análise",
    f"{conv_aprov_analise:.1f}%"
)

v6.metric(
    "Venda / Análise",
    f"{conv_venda_analise:.1f}%"
)

v7.metric(
    "Contatos por Análise",
    f"{contatos_por_analise:.1f}"
)

v8.metric(
    "Contatos por Venda",
    f"{contatos_por_venda:.1f}"
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
            "PROSPECT",
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
    "DATA_BASE_LABEL",
    "ATENDEU",
    "PROSPECT",
    "WHATSAPP ENVIADO",
    "CONTATO INVÁLIDO",
    "TOTAL"
]

colunas_exibir = [c for c in colunas_exibir if c in df_exibir.columns]

df_exibir = df_exibir.rename(
    columns={
        "DATA_BASE_LABEL": "DATA BASE"
    }
)

st.dataframe(
    df_exibir.rename(columns={"DATA_BASE_LABEL": "DATA BASE"}),
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
media_prospect = total_prospect / dias if dias > 0 else 0
media_whats = total_whatsapp / dias if dias > 0 else 0

m1, m2, m3, m4 = st.columns(4)

m1.metric(
    "Média Operacional",
    f"{media_total:.1f}"
)

m2.metric(
    "Média Atendeu",
    f"{media_atendeu:.1f}"
)

m3.metric(
    "Média Prospect",
    f"{media_prospect:.1f}"
)

m4.metric(
    "Média WhatsApp",
    f"{media_whats:.1f}"
)