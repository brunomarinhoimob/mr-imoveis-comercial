import streamlit as st
import pandas as pd
from datetime import timedelta, datetime
from login import tela_login



# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA (LOGIN vs DASHBOARD)
# ---------------------------------------------------------
if "logado" not in st.session_state or not st.session_state.logado:
    st.set_page_config(
        page_title="Painel Comercial",
        page_icon="🏠",
        layout="centered",
        initial_sidebar_state="collapsed"
    )
else:
    st.set_page_config(
        page_title="Painel Comercial",
        page_icon="🏠",
        layout="wide"
    )


# ---------------------------------------------------------
# CONTROLE DE LOGIN
# ---------------------------------------------------------
if "logado" not in st.session_state:
    st.session_state.logado = False


# ---------------------------------------------------------
# TELA DE LOGIN (BLOQUEIO TOTAL)
# ---------------------------------------------------------
if not st.session_state.logado:
    tela_login()
    st.stop()


# ---------------------------------------------------------
# AUTO REFRESH (para notificações e dados)
# ---------------------------------------------------------
from streamlit_autorefresh import st_autorefresh

st_autorefresh(interval=30 * 1000, key="auto_refresh_dashboard")

# 🔓 quebra cache no refresh automático
if "auto_refresh_dashboard" in st.session_state:
    st.session_state["refresh_planilha"] = True


# ---------------------------------------------------------
# ESTILO (CSS) – TEMA MIDNIGHT BLUE
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    :root {
        --mr-bg-main: #020617;
        --mr-bg-card: #020617;
        --mr-bg-card-soft: #0b1120;
        --mr-border-subtle: #1f2937;
        --mr-primary: #3b82f6;
        --mr-primary-soft: rgba(59,130,246,0.16);
        --mr-text-main: #e5e7eb;
        --mr-text-soft: #9ca3af;
        --mr-accent-green: #22c55e;
        --mr-accent-red: #ef4444;
    }

    .stApp {
        background: radial-gradient(circle at top left, #020617 0, #020617 40%, #020617 100%);
        color: var(--mr-text-main);
    }

    .main .block-container {
        max-width: 1400px;
        padding-top: 1.3rem;
        padding-bottom: 1.5rem;
        margin: 0 auto;
    }

    section[data-testid="stSidebar"] {
        background: #020617;
        border-right: 1px solid var(--mr-border-subtle);
    }
    section[data-testid="stSidebar"] * {
        color: var(--mr-text-main) !important;
    }

    h1, h2, h3, h4 {
        color: #e5e7eb;
        font-weight: 600;
    }

    p, span, label {
        color: var(--mr-text-soft);
    }

    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, var(--mr-bg-card-soft) 0%, #020617 100%);
        padding: 18px 16px;
        border-radius: 16px;
        box-shadow: 0 18px 35px rgba(0,0,0,0.55);
        border: 1px solid rgba(148,163,184,0.25);
    }
    div[data-testid="stMetric"] > label {
        font-size: 0.80rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #9ca3af;
    }
    div[data-testid="stMetric"] > div {
        font-size: 1.4rem;
        font-weight: 700;
        color: #e5e7eb;
    }

    hr {
        border: none;
        border-top: 1px solid rgba(148,163,184,0.25);
        margin: 1.4rem 0;
    }

    .stDataFrame {
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid rgba(148,163,184,0.25);
        box-shadow: 0 14px 30px rgba(0,0,0,0.45);
        background: var(--mr-bg-card);
    }

    .stDataFrame table thead tr th {
        background-color: #020617 !important;
        color: #e5e7eb !important;
        border-bottom: 1px solid rgba(148,163,184,0.25) !important;
        font-size: 0.78rem !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .stDataFrame table tbody tr:nth-child(odd) {
        background: #020617 !important;
    }
    .stDataFrame table tbody tr:nth-child(even) {
        background: #020617 !important;
    }
    .stDataFrame table tbody tr:hover {
        background: #111827 !important;
    }
    .dataframe tbody tr:hover {
        background: #111827 !important;
    }

    button[kind="primary"], button[data-baseweb="button"] {
        border-radius: 999px;
        background: linear-gradient(135deg, #1d4ed8 0%, #3b82f6 50%, #0ea5e9 100%);
        border: none;
        color: white;
        font-weight: 600;
        box-shadow: 0 10px 25px rgba(37,99,235,0.45);
    }
    button[kind="primary"]:hover, button[data-baseweb="button"]:hover {
        filter: brightness(1.05);
        box-shadow: 0 14px 30px rgba(37,99,235,0.6);
    }

    .stAlert {
        border-radius: 12px;
        border: 1px solid rgba(148,163,184,0.35);
        background: rgba(15,23,42,0.85);
    }

    .stSelectbox > div, .stTextInput > div, .stDateInput > div {
        background: #020617;
        border-radius: 10px;
        border: 1px solid rgba(148,163,184,0.35);
    }

    footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# LOGO
# ---------------------------------------------------------
LOGO_PATH = "logo_bruno_marinho.jpg"

try:
    st.sidebar.image(LOGO_PATH, use_container_width=True)
except Exception:
    pass

if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()


# ---------------------------------------------------------
# CONTROLE DE ACESSO POR PERFIL (MENU)
# ---------------------------------------------------------
perfil = st.session_state.get("perfil")

if perfil == "corretor":
    st.sidebar.markdown("### 👤 Acesso do Corretor")
    st.sidebar.markdown("- 📂 Carteira de Clientes")
    st.sidebar.markdown("- 🔎 Consulta de Clientes")
    st.sidebar.markdown("---")
    st.sidebar.warning("🔒 Demais páginas são restritas")


# ---------------------------------------------------------
# PLANILHA – GOOGLE SHEETS
# ---------------------------------------------------------
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID_ANALISES = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ANALISES}"


def limpar_para_data(serie: pd.Series) -> pd.Series:
    dt = pd.to_datetime(serie, dayfirst=True, errors="coerce")
    return dt.dt.date


def mes_ano_ptbr_para_date(valor: str):
    """
    Converte textos tipo 'novembro 2025' em date(2025, 11, 1).
    Se não conseguir, retorna NaT.
    """
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

    partes = s.split()

    try:
        mes_txt = partes[0]
        ano = int(partes[-1])
        mes_num = meses.get(mes_txt)

        if mes_num is None:
            return pd.NaT

        return datetime(ano, mes_num, 1).date()

    except Exception:
        return pd.NaT


@st.cache_data(ttl=60)
def carregar_dados_planilha(_refresh_key=None) -> pd.DataFrame:
    """
    Carrega e trata a base da planilha do Google Sheets.
    """
    df = pd.read_csv(CSV_URL)
    df.columns = [c.strip().upper() for c in df.columns]

    # DATA / DIA
    if "DATA" in df.columns:
        df["DIA"] = limpar_para_data(df["DATA"])
    elif "DIA" in df.columns:
        df["DIA"] = limpar_para_data(df["DIA"])
    else:
        df["DIA"] = pd.NaT

    # DATA BASE (MÊS COMERCIAL)
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
        base_raw = df[col_data_base].astype(str).str.strip()
        df["DATA_BASE_LABEL"] = base_raw.str.lower().str.title()
        df["DATA_BASE"] = base_raw.apply(mes_ano_ptbr_para_date)

        if df["DATA_BASE"].dropna().empty:
            df["DATA_BASE"] = df["DIA"]
            df["DATA_BASE_LABEL"] = df["DIA"].apply(
                lambda d: d.strftime("%m/%Y") if pd.notnull(d) else ""
            )
    else:
        df["DATA_BASE"] = df["DIA"]
        df["DATA_BASE_LABEL"] = df["DIA"].apply(
            lambda d: d.strftime("%m/%Y") if pd.notnull(d) else ""
        )

    # EQUIPE / CORRETOR
    for col in ["EQUIPE", "CORRETOR"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .fillna("NÃO INFORMADO")
                .astype(str)
                .str.upper()
                .str.strip()
            )
        else:
            df[col] = "NÃO INFORMADO"

    # STATUS BASE
    possiveis_cols_situacao = [
        "SITUAÇÃO",
        "SITUAÇÃO ATUAL",
        "STATUS",
        "SITUACAO",
        "SITUACAO ATUAL",
    ]
    col_situacao = next((c for c in possiveis_cols_situacao if c in df.columns), None)

    df["STATUS_BASE"] = ""

    if col_situacao:
        s = df[col_situacao].fillna("").astype(str).str.upper()

        df.loc[s.str.contains("EM ANÁLISE", na=False), "STATUS_BASE"] = "EM ANÁLISE"
        df.loc[s.str.contains("REANÁLISE", na=False), "STATUS_BASE"] = "REANÁLISE"

        # APROVAÇÕES SEPARADAS
        df.loc[s.str.strip() == "APROVAÇÃO", "STATUS_BASE"] = "APROVADO"

        df.loc[
            s.str.contains("APROVADO BACEN", na=False),
            "STATUS_BASE"
        ] = "APROVADO BACEN"

        df.loc[
            s.str.contains("APROVADO COM RESTRIÇÃO", na=False),
            "STATUS_BASE"
        ] = "APROVADO COM RESTRIÇÃO"

        df.loc[s.str.contains("REPROV", na=False), "STATUS_BASE"] = "REPROVADO"
        df.loc[s.str.contains("VENDA GERADA", na=False), "STATUS_BASE"] = "VENDA GERADA"
        df.loc[s.str.contains("VENDA INFORMADA", na=False), "STATUS_BASE"] = "VENDA INFORMADA"
        df.loc[s.str.contains("DESIST", na=False), "STATUS_BASE"] = "DESISTIU"

    # VGV
    if "OBSERVAÇÕES" in df.columns:
        df["VGV"] = pd.to_numeric(df["OBSERVAÇÕES"], errors="coerce").fillna(0)
    else:
        df["VGV"] = 0

    # NOME / CPF BASE
    possiveis_nome = ["NOME", "CLIENTE", "NOME CLIENTE", "NOME DO CLIENTE"]
    possiveis_cpf = ["CPF", "CPF CLIENTE", "CPF DO CLIENTE"]

    col_nome = next((c for c in possiveis_nome if c in df.columns), None)
    col_cpf = next((c for c in possiveis_cpf if c in df.columns), None)

    if col_nome is None:
        df["NOME_CLIENTE_BASE"] = "NÃO INFORMADO"
    else:
        df["NOME_CLIENTE_BASE"] = (
            df[col_nome]
            .fillna("NÃO INFORMADO")
            .astype(str)
            .str.upper()
            .str.strip()
        )

    if col_cpf is None:
        df["CPF_CLIENTE_BASE"] = ""
    else:
        df["CPF_CLIENTE_BASE"] = (
            df[col_cpf]
            .fillna("")
            .astype(str)
            .str.replace(r"\D", "", regex=True)
        )

    # CHAVE_CLIENTE global
    df["CHAVE_CLIENTE"] = (
        df["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO")
        + " | "
        + df["CPF_CLIENTE_BASE"].fillna("")
    )

    return df


# ---------------------------------------------------------
# CARREGA BASE COMPLETA
# ---------------------------------------------------------
df = carregar_dados_planilha(
    _refresh_key=st.session_state.get("refresh_planilha")
)




# ---------------------------------------------------------
# BOOTSTRAP DO APP
# ---------------------------------------------------------
from utils.bootstrap import iniciar_app
iniciar_app()


# ---------------------------------------------------------
# CONTEXTO DO USUÁRIO LOGADO
# ---------------------------------------------------------
perfil = st.session_state.get("perfil")
nome_corretor_logado = (
    st.session_state.get("nome_usuario", "")
    .upper()
    .strip()
)


# ---------------------------------------------------------
# BLOQUEIO GLOBAL DE DADOS PARA PERFIL CORRETOR
# ---------------------------------------------------------
if perfil == "corretor":
    if "CORRETOR" in df.columns:
        df = df[df["CORRETOR"] == nome_corretor_logado]

if df.empty:
    st.error("Erro ao carregar planilha.")
    st.stop()


# ---------------------------------------------------------
# STATUS FINAL DO CLIENTE
# ---------------------------------------------------------
df_ordenado_global = df.sort_values("DIA")
status_final_por_cliente = (
    df_ordenado_global.groupby("CHAVE_CLIENTE")["STATUS_BASE"].last().fillna("")
)
status_final_por_cliente.name = "STATUS_FINAL_CLIENTE"


# ---------------------------------------------------------
# SIDEBAR – FILTROS
# ---------------------------------------------------------
st.sidebar.title("Filtros 🔎")

modo_periodo = st.sidebar.radio(
    "Modo de filtro do período",
    ["Por DIA (data do registro)", "Por DATA BASE (mês comercial)"],
    index=0,
)

dias_validos = df["DIA"].dropna()
bases_validas = df["DATA_BASE"].dropna()

if dias_validos.empty and bases_validas.empty:
    st.error("Sem datas válidas na planilha para filtrar.")
    st.stop()

tipo_periodo = "DIA"
data_ini = None
data_fim = None
bases_selecionadas = []

if modo_periodo.startswith("Por DIA"):
    tipo_periodo = "DIA"
    data_min = dias_validos.min()
    data_max = dias_validos.max()
    data_ini_default = max(data_min, data_max - timedelta(days=30))

    periodo = st.sidebar.date_input(
        "Período por DIA",
        value=(data_ini_default, data_max),
        min_value=data_min,
        max_value=data_max,
    )
    data_ini, data_fim = periodo

else:
    tipo_periodo = "DATA_BASE"

    bases_df = (
        df[["DATA_BASE", "DATA_BASE_LABEL"]]
        .dropna(subset=["DATA_BASE"])
        .drop_duplicates()
        .sort_values("DATA_BASE")
    )

    opcoes = bases_df["DATA_BASE_LABEL"].tolist()

    if not opcoes:
        st.error("Sem datas base válidas na planilha para filtrar.")
        st.stop()

    default_labels = opcoes[-2:] if len(opcoes) >= 2 else opcoes

    bases_selecionadas = st.sidebar.multiselect(
        "Período por DATA BASE (mês comercial)",
        options=opcoes,
        default=default_labels,
    )

    if not bases_selecionadas:
        bases_selecionadas = opcoes

lista_equipes = sorted(df["EQUIPE"].unique())
equipe_sel = st.sidebar.selectbox("Equipe", ["Todas"] + lista_equipes)

if equipe_sel == "Todas":
    base_cor = df
else:
    base_cor = df[df["EQUIPE"] == equipe_sel]

lista_corretor = sorted(base_cor["CORRETOR"].unique())
corretor_sel = st.sidebar.selectbox("Corretor", ["Todos"] + lista_corretor)


# ---------------------------------------------------------
# FILTRO PRINCIPAL NA PLANILHA
# ---------------------------------------------------------
if tipo_periodo == "DIA":
    df_filtrado = df[
        (df["DIA"] >= data_ini) &
        (df["DIA"] <= data_fim)
    ].copy()
else:
    df_filtrado = df[df["DATA_BASE_LABEL"].isin(bases_selecionadas)].copy()

    dias_sel = df_filtrado["DIA"].dropna()

    if not dias_sel.empty:
        data_ini = dias_sel.min()
        data_fim = dias_sel.max()
    else:
        data_ini = dias_validos.min()
        data_fim = dias_validos.max()

if equipe_sel != "Todas":
    df_filtrado = df_filtrado[df_filtrado["EQUIPE"] == equipe_sel]

if corretor_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["CORRETOR"] == corretor_sel]

registros_filtrados = len(df_filtrado)


# ---------------------------------------------------------
# TÍTULO / CAPTION
# ---------------------------------------------------------
st.title("📊 Painel comercial")

if tipo_periodo == "DIA":
    label_periodo = "Período (DIA)"
    periodo_str = f"{data_ini.strftime('%d/%m/%Y')} até {data_fim.strftime('%d/%m/%Y')}"
else:
    label_periodo = "Período (DATA BASE)"

    if len(bases_selecionadas) == 1:
        periodo_str = bases_selecionadas[0]
    else:
        periodo_str = f"{bases_selecionadas[0]} até {bases_selecionadas[-1]}"

st.caption(
    f"{label_periodo}: {periodo_str} • Registros filtrados: {registros_filtrados}"
)


# ---------------------------------------------------------
# SELETOR DE VENDAS
# ---------------------------------------------------------
filtro_vendas = st.radio(
    "Tipo de vendas consideradas nos indicadores:",
    ["GERADAS + INFORMADAS", "Somente GERADAS"],
    index=0,
    horizontal=True,
)


# ---------------------------------------------------------
# CÁLCULOS PRINCIPAIS
# ---------------------------------------------------------
em_analise = (df_filtrado["STATUS_BASE"] == "EM ANÁLISE").sum()
reanalise = (df_filtrado["STATUS_BASE"] == "REANÁLISE").sum()
aprovacoes = (df_filtrado["STATUS_BASE"] == "APROVADO").sum()
aprovado_bacen = (df_filtrado["STATUS_BASE"] == "APROVADO BACEN").sum()
aprovado_restricao = (df_filtrado["STATUS_BASE"] == "APROVADO COM RESTRIÇÃO").sum()
reprovacoes = (df_filtrado["STATUS_BASE"] == "REPROVADO").sum()

analises_total = em_analise + reanalise

# Base de vendas: GERADA ou INFORMADA
df_vendas_ref = df_filtrado[
    df_filtrado["STATUS_BASE"].isin(["VENDA GERADA", "VENDA INFORMADA"])
].copy()

if not df_vendas_ref.empty:

    if "CHAVE_CLIENTE" not in df_vendas_ref.columns:
        df_vendas_ref["CHAVE_CLIENTE"] = (
            df_vendas_ref["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO")
            + " | "
            + df_vendas_ref["CPF_CLIENTE_BASE"].fillna("")
        )

    df_vendas_ref = df_vendas_ref.merge(
        status_final_por_cliente,
        on="CHAVE_CLIENTE",
        how="left",
    )

    df_vendas_ref = df_vendas_ref[
        df_vendas_ref["STATUS_FINAL_CLIENTE"] != "DESISTIU"
    ]

    if not df_vendas_ref.empty:
        df_vendas_ref = df_vendas_ref.sort_values("DIA")
        df_vendas_ult_base = df_vendas_ref.groupby("CHAVE_CLIENTE").tail(1)

        if filtro_vendas == "Somente GERADAS":
            df_vendas_ult = df_vendas_ult_base[
                df_vendas_ult_base["STATUS_BASE"] == "VENDA GERADA"
            ].copy()
        else:
            df_vendas_ult = df_vendas_ult_base.copy()

        if not df_vendas_ult.empty:
            venda_gerada = (df_vendas_ult["STATUS_BASE"] == "VENDA GERADA").sum()
            venda_informada = (df_vendas_ult["STATUS_BASE"] == "VENDA INFORMADA").sum()
            vendas_total = int(venda_gerada + venda_informada)

            vgv_total = df_vendas_ult["VGV"].sum()
            maior_vgv = df_vendas_ult["VGV"].max() if vendas_total > 0 else 0
        else:
            venda_gerada = 0
            venda_informada = 0
            vendas_total = 0
            vgv_total = 0
            maior_vgv = 0
    else:
        venda_gerada = 0
        venda_informada = 0
        vendas_total = 0
        vgv_total = 0
        maior_vgv = 0

else:
    venda_gerada = 0
    venda_informada = 0
    vendas_total = 0
    vgv_total = 0
    maior_vgv = 0

ticket_medio = (vgv_total / vendas_total) if vendas_total > 0 else 0

taxa_aprov_analise = (aprovacoes / analises_total * 100) if analises_total else 0
taxa_venda_analise = (vendas_total / analises_total * 100) if analises_total else 0
taxa_venda_aprov = (vendas_total / aprovacoes * 100) if aprovacoes else 0


# ---------------------------------------------------------
# CARDS – ANÁLISES & VENDAS
# ---------------------------------------------------------
st.subheader("Resumo de Análises & Vendas")

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Em análise", em_analise)
c2.metric("Reanálise", reanalise)
c3.metric("Aprovações", aprovacoes)
c4.metric("Aprovado Bacen", aprovado_bacen)
c5.metric("Aprov. Restrição", aprovado_restricao)
c6.metric("Reprovações", reprovacoes)

c7, c8, c9 = st.columns(3)
c7.metric("Vendas GERADAS (clientes)", int(venda_gerada))
c8.metric("Vendas INFORMADAS (clientes)", int(venda_informada))
c9.metric("Total Vendas (clientes)", int(vendas_total))

c10, c11, c12 = st.columns(3)
c10.metric("Aprov./Análises", f"{taxa_aprov_analise:.1f}%")
c11.metric("Vendas/Análises", f"{taxa_venda_analise:.1f}%")
c12.metric("Vendas/Aprovações", f"{taxa_venda_aprov:.1f}%")


# ---------------------------------------------------------
# INDICADORES DE VGV
# ---------------------------------------------------------
st.markdown("---")
st.subheader("💰 Indicadores de VGV (apenas clientes com venda)")


def format_currency(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


c13, c14, c15 = st.columns(3)
c13.metric("VGV Total", format_currency(vgv_total))
c14.metric("Ticket Médio", format_currency(ticket_medio))
c15.metric("Maior VGV", format_currency(maior_vgv))

st.markdown(
    "<hr><p style='text-align:center; color:#6b7280;'>"
    "Painel Comercial integrado ao Google Sheets"
    "</p>",
    unsafe_allow_html=True,
)