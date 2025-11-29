import streamlit as st
import pandas as pd
import requests
from datetime import timedelta, datetime

from utils.supremo_config import TOKEN_SUPREMO

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Imobiliária – MR Imóveis",
    page_icon="🏠",
    layout="wide",
)

# ---------------------------------------------------------
# ESTILO (CSS) – TEMA MIDNIGHT BLUE MR
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

    /* fundo geral */
    .stApp {
        background: radial-gradient(circle at top left, #020617 0, #020617 40%, #020617 100%);
        color: var(--mr-text-main);
    }

    /* container central */
    .main .block-container {
        max-width: 1400px;
        padding-top: 1.3rem;
        padding-bottom: 1.5rem;
        margin: 0 auto;
    }

    /* sidebar */
    section[data-testid="stSidebar"] {
        background: #020617;
        border-right: 1px solid var(--mr-border-subtle);
    }
    section[data-testid="stSidebar"] * {
        color: var(--mr-text-main) !important;
    }

    /* títulos */
    h1, h2, h3, h4 {
        color: #e5e7eb;
        font-weight: 600;
    }

    /* textos secundários */
    p, span, label {
        color: var(--mr-text-soft);
    }

    /* métricas (st.metric) em cards premium */
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

    /* separadores (---) */
    hr {
        border: none;
        border-top: 1px solid rgba(148,163,184,0.25);
        margin: 1.4rem 0;
    }

    /* tabelas / dataframes */
    .stDataFrame {
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid rgba(148,163,184,0.25);
        box-shadow: 0 14px 30px rgba(0,0,0,0.45);
        background: var(--mr-bg-card);
    }

    /* tentativas de estilizar cabeçalho/linhas (pode variar por versão) */
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

    /* hover de tabelas HTML simples (st.table / pandas styler) */
    .dataframe tbody tr:hover {
        background: #111827 !important;
    }

    /* botões padrão */
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

    /* alerts (st.info, st.warning, etc.) */
    .stAlert {
        border-radius: 12px;
        border: 1px solid rgba(148,163,184,0.35);
        background: rgba(15,23,42,0.85);
    }

    /* inputs / selects / date */
    .stSelectbox > div, .stTextInput > div, .stDateInput > div {
        background: #020617;
        border-radius: 10px;
        border: 1px solid rgba(148,163,184,0.35);
    }

    /* rodapé padrão do Streamlit escondido */
    footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# LOGO
# ---------------------------------------------------------
LOGO_PATH = "logo_mr.png"
try:
    st.sidebar.image(LOGO_PATH, use_container_width=True)
except Exception:
    pass

# ---------------------------------------------------------
# PLANILHA – GOOGLE SHEETS
# ---------------------------------------------------------
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID_ANALISES = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ANALISES}"


def limpar_para_data(serie: pd.Series) -> pd.Series:
    dt = pd.to_datetime(serie, dayfirst=True, errors="coerce")
    return dt.dt.date


@st.cache_data(ttl=300)
def carregar_dados_planilha() -> pd.DataFrame:
    """
    Carrega e trata a base da planilha do Google Sheets.
    Cache de 5 minutos para não ficar batendo toda hora na planilha.
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
        df.loc[s.str.contains("EM ANÁLISE"), "STATUS_BASE"] = "EM ANÁLISE"
        df.loc[s.str.contains("REANÁLISE"), "STATUS_BASE"] = "REANÁLISE"
        df.loc[s.str.contains("APROV"), "STATUS_BASE"] = "APROVADO"
        df.loc[s.str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
        df.loc[s.str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA GERADA"
        df.loc[s.str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA INFORMADA"

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

    return df


df = carregar_dados_planilha()

if df.empty:
    st.error("Erro ao carregar planilha.")
    st.stop()

# ---------------------------------------------------------
# LEADS – API SUPREMO (CACHE 1 HORA E COLUNAS NORMALIZADAS)
# ---------------------------------------------------------
BASE_URL_LEADS = "https://api.supremocrm.com.br/v1/leads"


@st.cache_data(ttl=3600)
def carregar_leads_direto(limit: int = 1000, max_pages: int = 100) -> pd.DataFrame:
    """
    Carrega leads da API do Supremo.
    Cache de 1 hora para evitar múltiplas chamadas pesadas.
    Normaliza:
      - data_captura -> datetime + data_captura_date
      - nome_corretor_norm (maiúsculo)
      - equipe_lead_norm, se existir coluna de equipe.
    """
    headers = {"Authorization": f"Bearer {TOKEN_SUPREMO}"}

    dfs = []
    total = 0
    pagina = 1

    while total < limit and pagina <= max_pages:
        params = {"pagina": pagina}
        try:
            resp = requests.get(
                BASE_URL_LEADS,
                headers=headers,
                params=params,
                timeout=30,
            )
        except Exception:
            break

        if resp.status_code != 200:
            break

        try:
            data = resp.json()
        except Exception:
            break

        if isinstance(data, dict) and "data" in data:
            df_page = pd.DataFrame(data["data"])
        elif isinstance(data, list):
            df_page = pd.DataFrame(data)
        else:
            df_page = pd.DataFrame()

        if df_page.empty:
            break

        dfs.append(df_page)
        total += len(df_page)
        pagina += 1

    if not dfs:
        return pd.DataFrame()

    df_all = pd.concat(dfs, ignore_index=True)

    # Remove duplicados por ID (se existir)
    if "id" in df_all.columns:
        df_all = df_all.drop_duplicates(subset="id")

    # Datas
    if "data_captura" in df_all.columns:
        df_all["data_captura"] = pd.to_datetime(
            df_all["data_captura"], errors="coerce"
        )
        df_all["data_captura_date"] = df_all["data_captura"].dt.date
    else:
        df_all["data_captura_date"] = pd.NaT

    # Nome do corretor (para filtro por corretor)
    if "nome_corretor" in df_all.columns:
        df_all["nome_corretor_norm"] = (
            df_all["nome_corretor"]
            .fillna("NÃO INFORMADO")
            .astype(str)
            .str.upper()
            .str.strip()
        )
    else:
        df_all["nome_corretor_norm"] = "NÃO INFORMADO"

    # Equipe do lead, se existir
    possiveis_equipes = ["equipe", "nome_equipe", "equipe_nome", "nome_equipe_lead"]
    col_equipe = next((c for c in possiveis_equipes if c in df_all.columns), None)
    if col_equipe:
        df_all["equipe_lead_norm"] = (
            df_all[col_equipe]
            .fillna("NÃO INFORMADO")
            .astype(str)
            .str.upper()
            .str.strip()
        )
    else:
        df_all["equipe_lead_norm"] = "NÃO INFORMADO"

    return df_all.head(limit)

# ---------------------------------------------------------
# SIDEBAR – FILTROS
# ---------------------------------------------------------
st.sidebar.title("Filtros 🔎")

dias_validos = df["DIA"].dropna()
data_min = dias_validos.min()
data_max = dias_validos.max()

# padrão: últimos 30 dias (ou menos se não tiver tudo isso)
data_ini_default = max(data_min, data_max - timedelta(days=30))

periodo = st.sidebar.date_input(
    "Período",
    value=(data_ini_default, data_max),
    min_value=data_min,
    max_value=data_max,
)

data_ini, data_fim = periodo

lista_equipes = sorted(df["EQUIPE"].unique())
equipe_sel = st.sidebar.selectbox("Equipe", ["Todas"] + lista_equipes)

if equipe_sel == "Todas":
    base_cor = df
else:
    base_cor = df[df["EQUIPE"] == equipe_sel]

lista_corretor = sorted(base_cor["CORRETOR"].unique())
corretor_sel = st.sidebar.selectbox("Corretor", ["Todos"] + lista_corretor)

# ---------------------------------------------------------
# BOTÃO PARA ATUALIZAR LEADS DO CRM MANUALMENTE
# ---------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.write("🔄 Atualização de Leads (CRM)")

btn_atualizar_leads = st.sidebar.button("Atualizar Leads do CRM agora")

# Se clicar, limpa o cache e o df_leads salvo na sessão.
if btn_atualizar_leads:
    st.cache_data.clear()
    st.session_state.pop("df_leads", None)

# Carrega os leads (já respeitando cache ou renovando se o botão foi clicado)
df_leads = carregar_leads_direto()

# Mantém em sessão para uso nas outras páginas (Vendas, Funis, etc.)
if "df_leads" not in st.session_state:
    st.session_state["df_leads"] = df_leads

# ---------------------------------------------------------
# FILTRO PRINCIPAL NA PLANILHA
# ---------------------------------------------------------
df_filtrado = df[
    (df["DIA"] >= data_ini) &
    (df["DIA"] <= data_fim)
].copy()

if equipe_sel != "Todas":
    df_filtrado = df_filtrado[df_filtrado["EQUIPE"] == equipe_sel]

if corretor_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["CORRETOR"] == corretor_sel]

registros_filtrados = len(df_filtrado)

# ---------------------------------------------------------
# TÍTULO
# ---------------------------------------------------------
st.title("📊 Dashboard Imobiliária – MR Imóveis")
st.caption(
    f"Período: {data_ini.strftime('%d/%m/%Y')} até {data_fim.strftime('%d/%m/%Y')} • "
    f"Registros filtrados: {registros_filtrados}"
)

# ---------------------------------------------------------
# CÁLCULOS PRINCIPAIS (PLANILHA)
# ---------------------------------------------------------
em_analise = (df_filtrado["STATUS_BASE"] == "EM ANÁLISE").sum()
reanalise = (df_filtrado["STATUS_BASE"] == "REANÁLISE").sum()
aprovacoes = (df_filtrado["STATUS_BASE"] == "APROVADO").sum()
reprovacoes = (df_filtrado["STATUS_BASE"] == "REPROVADO").sum()

analises_total = em_analise + reanalise

df_vendas_ref = df_filtrado[
    df_filtrado["STATUS_BASE"].isin(["VENDA GERADA", "VENDA INFORMADA"])
].copy()

if not df_vendas_ref.empty:
    df_vendas_ref["CHAVE_CLIENTE"] = (
        df_vendas_ref["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO")
        + " | "
        + df_vendas_ref["CPF_CLIENTE_BASE"].fillna("")
    )

    df_vendas_ref = df_vendas_ref.sort_values("DIA")
    df_vendas_ult = df_vendas_ref.groupby("CHAVE_CLIENTE").tail(1)

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

ticket_medio = (vgv_total / vendas_total) if vendas_total > 0 else 0

taxa_aprov_analise = (aprovacoes / analises_total * 100) if analises_total else 0
taxa_venda_analise = (vendas_total / analises_total * 100) if analises_total else 0
taxa_venda_aprov = (vendas_total / aprovacoes * 100) if aprovacoes else 0

# ---------------------------------------------------------
# CARDS – ANÁLISES & VENDAS
# ---------------------------------------------------------
st.subheader("Resumo de Análises & Vendas")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Em análise", em_analise)
c2.metric("Reanálise", reanalise)
c3.metric("Aprovações", aprovacoes)
c4.metric("Reprovações", reprovacoes)

c5, c6, c7 = st.columns(3)
c5.metric("Vendas GERADAS (clientes)", int(venda_gerada))
c6.metric("Vendas INFORMADAS (clientes)", int(venda_informada))
c7.metric("Total Vendas (clientes)", int(vendas_total))

c8, c9, c10 = st.columns(3)
c8.metric("Aprov./Análises", f"{taxa_aprov_analise:.1f}%")
c9.metric("Vendas/Análises", f"{taxa_venda_analise:.1f}%")
c10.metric("Vendas/Aprovações", f"{taxa_venda_aprov:.1f}%")

# ---------------------------------------------------------
# LEADS – RESUMO (RESPEITANDO PERÍODO + EQUIPE + CORRETOR)
# ---------------------------------------------------------
st.markdown("---")
st.subheader("📈 Resumo de Leads (Supremo CRM)")

df_leads_use = df_leads.copy()

if not df_leads_use.empty and "data_captura_date" in df_leads_use.columns:
    # Filtro por período
    df_leads_use = df_leads_use.dropna(subset=["data_captura_date"])
    df_leads_use = df_leads_use[
        (df_leads_use["data_captura_date"] >= data_ini)
        & (df_leads_use["data_captura_date"] <= data_fim)
    ]

    # Filtro por equipe (se tiver coluna de equipe nos leads)
    if equipe_sel != "Todas" and "equipe_lead_norm" in df_leads_use.columns:
        df_leads_use = df_leads_use[
            df_leads_use["equipe_lead_norm"] == equipe_sel
        ]

    # Filtro por corretor
    if corretor_sel != "Todos" and "nome_corretor_norm" in df_leads_use.columns:
        df_leads_use = df_leads_use[
            df_leads_use["nome_corretor_norm"] == corretor_sel
        ]

    total_leads_periodo = len(df_leads_use)

    # Texto dinâmico da métrica principal
    if corretor_sel != "Todos":
        label_leads = "Leads do corretor (período filtrado)"
    elif equipe_sel != "Todas":
        label_leads = "Leads da equipe (período filtrado)"
    else:
        label_leads = "Leads da imobiliária (período filtrado)"

    cL1, cL2, cL3 = st.columns(3)
    cL1.metric(label_leads, total_leads_periodo)

    # Corretores com leads nesse filtro
    if "nome_corretor_norm" in df_leads_use.columns and not df_leads_use.empty:
        qtd_corretor = df_leads_use["nome_corretor_norm"].nunique()
        cL2.metric("Corretores com leads no período", qtd_corretor)

        if qtd_corretor > 0:
            media_leads = total_leads_periodo / qtd_corretor
            cL3.metric("Média de leads por corretor", f"{media_leads:.1f}")
        else:
            cL3.metric("Média de leads por corretor", "-")
    else:
        cL2.metric("Corretores com leads no período", "-")
        cL3.metric("Média de leads por corretor", "-")
else:
    st.info("Nenhum lead carregado ou campo 'data_captura' ausente na base.")

# ---------------------------------------------------------
# INDICADORES DE VGV
# ---------------------------------------------------------
st.markdown("---")
st.subheader("💰 Indicadores de VGV (apenas clientes com venda)")


def format_currency(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


c11, c12, c13 = st.columns(3)
c11.metric("VGV Total", format_currency(vgv_total))
c12.metric("Ticket Médio", format_currency(ticket_medio))
c13.metric("Maior VGV", format_currency(maior_vgv))

st.markdown(
    "<hr><p style='text-align:center; color:#6b7280;'>"
    "Dashboard MR Imóveis integrado ao Google Sheets + Supremo CRM"
    "</p>",
    unsafe_allow_html=True,
)
