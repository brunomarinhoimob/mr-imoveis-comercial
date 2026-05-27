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
def normalizar_texto(texto):
    return (
        str(texto)
        .upper()
        .strip()
    )

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

    except:
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

    col_data_base = next(
        (c for c in possiveis_cols_base if c in df.columns),
        None
    )

    if col_data_base:

        base_raw = (
            df[col_data_base]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        df["DATA_BASE_LABEL"] = (
            base_raw
            .str.lower()
            .str.title()
        )

        df["DATA_BASE"] = (
            base_raw.apply(mes_ano_ptbr_para_date)
        )

    else:

        df["DATA_BASE_LABEL"] = ""
        df["DATA_BASE"] = pd.NaT

    return df

# =========================================================
# CARREGAR PRODUÇÃO
# =========================================================
@st.cache_data(ttl=30)
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
        "LEADS QUENTES",
        "LEADS FRIOS",
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
# CARREGAR PROCESSOS
# =========================================================
@st.cache_data(ttl=30)
def carregar_processos():

    dfp = pd.read_csv(CSV_PROCESSOS)

    dfp.columns = [c.strip().upper() for c in dfp.columns]

    if "DATA" in dfp.columns:
        dfp["DATA"] = pd.to_datetime(dfp["DATA"], dayfirst=True, errors="coerce")
    elif "DIA" in dfp.columns:
        dfp["DATA"] = pd.to_datetime(dfp["DIA"], dayfirst=True, errors="coerce")
    else:
        dfp["DATA"] = pd.NaT

    dfp = tratar_data_base(dfp)

    possiveis_status = ["SITUAÇÃO", "SITUACAO", "STATUS", "SITUAÇÃO ATUAL", "SITUACAO ATUAL"]
    col_status = next((c for c in possiveis_status if c in dfp.columns), None)

    if col_status:
        dfp["STATUS_ORIGINAL"] = dfp[col_status].fillna("").astype(str).str.upper().str.strip()
    else:
        dfp["STATUS_ORIGINAL"] = ""

    dfp["STATUS_BASE"] = ""

    # ---- LIMPEZA DE ACENTOS E MAPEMENTO ----
    s_sem_acento = (
        dfp["STATUS_ORIGINAL"]
        .str.normalize('NFKD')
        .str.encode('ascii', errors='ignore')
        .str.decode('utf-8')
    )

    dfp.loc[s_sem_acento == "EM ANALISE", "STATUS_BASE"] = "EM ANALISE"
    dfp.loc[s_sem_acento == "REANALISE", "STATUS_BASE"] = "REANALISE"
    dfp.loc[s_sem_acento == "APROVACAO", "STATUS_BASE"] = "APROVADO"
    dfp.loc[s_sem_acento == "APROVADO BACEN", "STATUS_BASE"] = "APROVADO BACEN"
    dfp.loc[s_sem_acento == "APROVADO COM RESTRICAO", "STATUS_BASE"] = "APROVADO COM RESTRICAO"
    dfp.loc[s_sem_acento == "REPROVACAO", "STATUS_BASE"] = "REPROVADO"
    dfp.loc[s_sem_acento == "VENDA GERADA", "STATUS_BASE"] = "VENDA GERADA"
    dfp.loc[s_sem_acento == "VENDA INFORMADA", "STATUS_BASE"] = "VENDA INFORMADA"
    dfp.loc[s_sem_acento == "PENDENCIA", "STATUS_BASE"] = "PENDENCIA"
    dfp.loc[s_sem_acento == "DESISTIU", "STATUS_BASE"] = "DESISTIU"

    if "ORIGEM" not in dfp.columns:
        dfp["ORIGEM"] = ""

    dfp["ORIGEM"] = (
        dfp["ORIGEM"]
        .fillna("")
        .astype(str)
        .str.upper()
        .str.strip()
        .str.normalize('NFKD')
        .str.encode('ascii', errors='ignore')
        .str.decode('utf-8')
    )
    # ----------------------------------------

    possiveis_nome = ["NOME", "CLIENTE", "NOME CLIENTE"]
    possiveis_cpf = ["CPF", "CPF CLIENTE"]

    col_nome = next((c for c in possiveis_nome if c in dfp.columns), None)
    col_cpf = next((c for c in possiveis_cpf if c in dfp.columns), None)

    if col_nome:
        dfp["NOME_CLIENTE_BASE"] = dfp[col_nome].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
    else:
        dfp["NOME_CLIENTE_BASE"] = "NÃO INFORMADO"

    if col_cpf:
        dfp["CPF_CLIENTE_BASE"] = dfp[col_cpf].fillna("").astype(str).str.replace(r"\D", "", regex=True)
    else:
        dfp["CPF_CLIENTE_BASE"] = ""

    dfp["CHAVE_CLIENTE"] = dfp["NOME_CLIENTE_BASE"] + " | " + dfp["CPF_CLIENTE_BASE"]

    return dfp

# =========================================================
# CARREGAMENTO
# =========================================================
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
# VALIDAÇÕES
# =========================================================
if df.empty:
    st.warning("Sem dados.")
    st.stop()

df = df[df["DATA"].notna()].copy()

if df.empty:
    st.warning("Sem datas válidas.")
    st.stop()

# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.title("Filtros 🔎")

modo_periodo = st.sidebar.radio(
    "Modo de filtro",
    ["Por DATA BASE", "Por DATA"],
    index=0
)

if modo_periodo == "Por DATA BASE":

    bases_df = (
        df[
            ["DATA_BASE", "DATA_BASE_LABEL"]
        ]
        .dropna(subset=["DATA_BASE"])
        .drop_duplicates()
        .sort_values("DATA_BASE")
    )

    opcoes_base = bases_df["DATA_BASE_LABEL"].tolist()

    ultima_base = opcoes_base[-1]

    data_base_sel = st.sidebar.selectbox(
        "DATA BASE",
        opcoes_base,
        index=opcoes_base.index(ultima_base)
    )

    df = df[
        df["DATA_BASE_LABEL"] == data_base_sel
    ].copy()

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
        (df["DATA"].dt.date >= data_ini)
        &
        (df["DATA"].dt.date <= data_fim)
    ].copy()

# =========================================================
# PROCESSOS
# =========================================================
df_processos = df_processos[
    df_processos["DATA"].notna()
].copy()

df_processos_periodo = df_processos[
    (df_processos["DATA"].dt.date >= data_ini)
    &
    (df_processos["DATA"].dt.date <= data_fim)
].copy()

# =========================================================
# TOTAL
# =========================================================
df["TOTAL_CALCULADO"] = (
    df["ATENDEU"]
    + df["WHATSAPP ENVIADO"]
    + df["CONTATO INVÁLIDO"]
)

df["TOTAL"] = df["TOTAL"].fillna(0)

df.loc[
    df["TOTAL"] == 0,
    "TOTAL"
] = df.loc[
    df["TOTAL"] == 0,
    "TOTAL_CALCULADO"
]

# =========================================================
# KPIS
# =========================================================
total_atendeu = int(df["ATENDEU"].sum())
total_prospect = int(df["PROSPECT"].sum())
total_whatsapp = int(df["WHATSAPP ENVIADO"].sum())
total_invalido = int(df["CONTATO INVÁLIDO"].sum())
total_leads_quentes = int(df["LEADS QUENTES"].sum())
total_leads_frios = int(df["LEADS FRIOS"].sum())
total_operacional = int(df["TOTAL"].sum())

taxa_prospect = (
    (total_prospect / total_operacional) * 100
    if total_operacional > 0 else 0
)

# =========================================================
# CLIENTES ÚNICOS
# =========================================================
df_clientes_unicos = pd.DataFrame(
    columns=["CHAVE_CLIENTE", "STATUS_BASE", "ORIGEM"]
)

# =========================================================
# BASE HISTÓRICA DE ANÁLISES
# =========================================================
df_historico_analises = pd.DataFrame()

if not df_processos_periodo.empty:

    # Ordena por data
    df_processos_periodo = (
        df_processos_periodo
        .sort_values(by="DATA", ascending=True)
        .reset_index(drop=True)
    )

    # =====================================================
    # HISTÓRICO COMPLETO DE ANÁLISES
    # =====================================================
    df_historico_analises = df_processos_periodo[
        df_processos_periodo["STATUS_BASE"] == "EM ANALISE"
    ].copy()

    # =====================================================
    # ÚLTIMO STATUS REAL DO CLIENTE
    # =====================================================
    df_ultimos_registros = (
        df_processos_periodo
        .groupby("CHAVE_CLIENTE", as_index=False)
        .last()
    )

    df_clientes_unicos = df_ultimos_registros.copy()

# =========================================================
# CONTAGEM DE ANÁLISES
# =========================================================
analises = len(df_historico_analises)

# =========================================================
# CONTAGEM STATUS ATUAL
# =========================================================
pendencias = int(
    (df_clientes_unicos["STATUS_BASE"] == "PENDENCIA").sum()
)

desistencias = int(
    (df_clientes_unicos["STATUS_BASE"] == "DESISTIU").sum()
)

aprovacoes = int(
    (df_clientes_unicos["STATUS_BASE"] == "APROVADO").sum()
)

aprovado_bacen = int(
    (df_clientes_unicos["STATUS_BASE"] == "APROVADO BACEN").sum()
)

aprovado_restricao = int(
    (df_clientes_unicos["STATUS_BASE"] == "APROVADO COM RESTRICAO").sum()
)

vendas = int(
    df_clientes_unicos["STATUS_BASE"]
    .isin(["VENDA GERADA", "VENDA INFORMADA"])
    .sum()
)
# =========================================================
# ORIGENS
# =========================================================

df_analises_ativas = df_historico_analises.copy()

total_em_analise_estrito = len(df_analises_ativas)

origens_alvo = [
    "INDICACAO",
    "ORGANICO",
    "LISTA",
    "C2S",
    "INSTAGRAM",
    "TRAFEGO"
]

recap_origens = {}

for orig in origens_alvo:

    qtd = int(
        (df_analises_ativas["ORIGEM"] == orig)
        .sum()
    )

    pct = (
        (qtd / total_em_analise_estrito) * 100
        if total_em_analise_estrito > 0 else 0
    )

    recap_origens[orig] = {
        "qtd": qtd,
        "pct": pct
    }

# =========================================================
# CARDS
# =========================================================
c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "📞 Total Operacional",
    total_operacional
)

c2.metric(
    "🔥 Leads Quentes",
    total_leads_quentes
)

c3.metric(
    "❄️ Leads Frios",
    total_leads_frios
)

c4.metric(
    "📊 Taxa Prospect",
    f"{taxa_prospect:.1f}%"
)

st.markdown("---")

p1, p2, p3, p4 = st.columns(4)

p1.metric("✅ Atendeu", total_atendeu)
p2.metric("🔥 Prospect", total_prospect)
p3.metric("💬 WhatsApp", total_whatsapp)
p4.metric("🚫 Inválido", total_invalido)

# =========================================================
# RESULTADO
# =========================================================
st.markdown("---")

st.subheader("🎯 Resultado")

r1, r2, r3, r4, r5, r6, r7 = st.columns(7)

r1.metric("📄 Análises", analises)
r2.metric("⏳ Pendência", pendencias)
r3.metric("✅ Aprovações", aprovacoes)
r4.metric("🟡 Restrição", aprovado_restricao)
r5.metric("🏦 BACEN", aprovado_bacen)
r6.metric("💰 Vendas", vendas)
r7.metric("❌ Desistência", desistencias)

# =========================================================
# ORIGEM DAS ANÁLISES
# =========================================================
st.markdown("---")

st.subheader(
    f"🧠 Origem das Análises Atuais (Total: {total_em_analise_estrito})"
)

o1, o2, o3, o4, o5, o6 = st.columns(6)

cards_origem = [
    ("📢 Indicação", "INDICACAO", o1),
    ("🌱 Orgânico", "ORGANICO", o2),
    ("📋 Lista", "LISTA", o3),
    ("💻 C2S", "C2S", o4),
    ("📸 Instagram", "INSTAGRAM", o5),
    ("🎯 Tráfego", "TRAFEGO", o6),
]

for titulo, chave, coluna in cards_origem:

    qtd = recap_origens[chave]["qtd"]
    pct = recap_origens[chave]["pct"]

    coluna.markdown(
        f"""
        <div style="
            background: linear-gradient(145deg, #0f172a 0%, #020617 100%);
            border: 1px solid rgba(148,163,184,0.20);
            padding: 18px;
            border-radius: 18px;
            text-align: center;
        ">

            <div style="
                color: #94a3b8;
                font-size: 14px;
                margin-bottom: 10px;
            ">
                {titulo}
            </div>

            <div style="
                color: white;
                font-size: 34px;
                font-weight: 700;
                line-height: 1;
            ">
                {qtd}
            </div>

            <div style="
                color: #94a3b8;
                font-size: 13px;
                margin-top: 6px;
            ">
                {pct:.1f}%
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

o1, o2, o3, o4, o5, o6 = st.columns(6)

o1.metric(
    "📢 Indicação",
    f'{recap_origens["INDICACAO"]["qtd"]} ({recap_origens["INDICACAO"]["pct"]:.1f}%)'
)

o2.metric(
    "🌱 Orgânico",
    f'{recap_origens["ORGANICO"]["qtd"]} ({recap_origens["ORGANICO"]["pct"]:.1f}%)'
)

o3.metric(
    "📋 Lista",
    f'{recap_origens["LISTA"]["qtd"]} ({recap_origens["LISTA"]["pct"]:.1f}%)'
)

o4.metric(
    "💻 C2S",
    f'{recap_origens["C2S"]["qtd"]} ({recap_origens["C2S"]["pct"]:.1f}%)'
)

o5.metric(
    "📸 Instagram",
    f'{recap_origens["INSTAGRAM"]["qtd"]} ({recap_origens["INSTAGRAM"]["pct"]:.1f}%)'
)

o6.metric(
    "🎯 Tráfego",
    f'{recap_origens["TRAFEGO"]["qtd"]} ({recap_origens["TRAFEGO"]["pct"]:.1f}%)'
)

# =========================================================
# GRÁFICO
# =========================================================
st.markdown("---")

st.subheader("📈 Evolução diária")

chart = (
    alt.Chart(df)
    .transform_fold(
        [
            "ATENDEU",
            "PROSPECT",
            "WHATSAPP ENVIADO",
            "CONTATO INVÁLIDO",
            "LEADS QUENTES"
        ],
        as_=["Tipo", "Quantidade"]
    )
    .mark_line(point=True)
    .encode(
        x=alt.X("DATA:T", title="Data"),
        y=alt.Y("Quantidade:Q", title="Quantidade"),
        color="Tipo:N"
    )
    .properties(height=450)
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

df_exibir["DATA"] = (
    df_exibir["DATA"]
    .dt.strftime("%d/%m/%Y")
)

colunas_exibir = [
    "DATA",
    "DATA_BASE_LABEL",
    "ATENDEU",
    "PROSPECT",
    "WHATSAPP ENVIADO",
    "CONTATO INVÁLIDO",
    "LEADS QUENTES",
    "LEADS FRIOS",
    "TOTAL"
]

colunas_exibir = [
    c for c in colunas_exibir
    if c in df_exibir.columns
]

df_exibir = df_exibir[colunas_exibir].copy()

df_exibir = df_exibir.rename(
    columns={
        "DATA_BASE_LABEL": "DATA BASE"
    }
)

for col in df_exibir.columns:
    df_exibir[col] = df_exibir[col].astype(str)

st.dataframe(
    df_exibir,
    use_container_width=True,
    hide_index=True
)

# =========================================================
# MÉDIA
# =========================================================
st.markdown("---")

st.subheader("📌 Média diária")

dias = df["DATA"].dt.date.nunique()

media_total = (
    total_operacional / dias
    if dias > 0 else 0
)

media_atendeu = (
    total_atendeu / dias
    if dias > 0 else 0
)

media_prospect = (
    total_prospect / dias
    if dias > 0 else 0
)

media_quente = (
    total_leads_quentes / dias
    if dias > 0 else 0
)

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
    "Média Leads Quentes",
    f"{media_quente:.1f}"
)

# =========================================================
# TABELA ANÁLISES
# =========================================================
st.markdown("---")

st.subheader(
    "📋 Situação Real das Análises"
)

if not df_processos_periodo.empty:

    df_lista_analises = (
        df_processos_periodo
        .sort_values(by="DATA", ascending=True)
    )

    df_lista_analises = (
        df_lista_analises
        .drop_duplicates(
            subset=["CHAVE_CLIENTE"],
            keep="last"
        )
        .copy()
    )

    if "DATA" in df_lista_analises.columns:

        df_lista_analises["DATA_FORMATADA"] = (
            df_lista_analises["DATA"]
            .dt.strftime("%d/%m/%Y")
        )

    else:

        df_lista_analises["DATA_FORMATADA"] = ""

    colunas_finais = []
    nomes_amigaveis = {}

    if "DATA_FORMATADA" in df_lista_analises.columns:

        colunas_finais.append("DATA_FORMATADA")
        nomes_amigaveis["DATA_FORMATADA"] = "DATA REGISTRO"

    if "NOME_CLIENTE_BASE" in df_lista_analises.columns:

        colunas_finais.append("NOME_CLIENTE_BASE")
        nomes_amigaveis["NOME_CLIENTE_BASE"] = "CLIENTE"

    if "STATUS_BASE" in df_lista_analises.columns:

        colunas_finais.append("STATUS_BASE")
        nomes_amigaveis["STATUS_BASE"] = "SITUAÇÃO ATUAL"

    if "ORIGEM" in df_lista_analises.columns:

        colunas_finais.append("ORIGEM")
        nomes_amigaveis["ORIGEM"] = "ORIGEM"

    for col_extra in ["CORRETOR", "GERENTE"]:

        if col_extra in df_lista_analises.columns:

            colunas_finais.append(col_extra)
            nomes_amigaveis[col_extra] = col_extra

    df_tabela_analises = (
        df_lista_analises[colunas_finais]
        .copy()
    )

    df_tabela_analises = (
        df_tabela_analises
        .rename(columns=nomes_amigaveis)
    )

    st.dataframe(
        df_tabela_analises,
        use_container_width=True,
        hide_index=True
    )

else:

    st.info(
        "Nenhuma análise encontrada."
    )