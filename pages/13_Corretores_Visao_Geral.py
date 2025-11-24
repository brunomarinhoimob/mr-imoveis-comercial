import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import date, datetime, timedelta

from app_dashboard import carregar_dados_planilha, carregar_leads_direto
from utils.supremo_config import TOKEN_SUPREMO

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Corretores – Visão Geral",
    page_icon="🧑‍💼",
    layout="wide",
)

# ---------------------------------------------------------
# ESTILO (CSS)
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp {
        background-color: #050814;
        color: #f9fafb;
    }

    .main-title {
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 0.3rem;
    }

    .sub-title {
        font-size: 0.95rem;
        color: #9ca3af;
        margin-bottom: 1.5rem;
    }

    .metric-card {
        background: #020617;
        padding: 16px 20px;
        border-radius: 18px;
        box-shadow: 0 12px 30px rgba(0,0,0,0.6);
        border: 1px solid #1f2937;
        text-align: left;
        margin-bottom: 1rem;
    }

    .metric-label {
        font-size: 0.75rem;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 6px;
    }

    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #e5e7eb;
    }

    .metric-help {
        font-size: 0.8rem;
        color: #6b7280;
        margin-top: 3px;
    }

    .section-title {
        font-size: 1.1rem;
        font-weight: 600;
        margin: 1.5rem 0 0.6rem 0;
    }

    .badge {
        display: inline-flex;
        align-items: center;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-left: 6px;
    }

    .badge-green {
        background: rgba(22, 163, 74, 0.1);
        color: #4ade80;
        border: 1px solid rgba(22, 163, 74, 0.4);
    }

    .badge-red {
        background: rgba(220, 38, 38, 0.1);
        color: #f87171;
        border: 1px solid rgba(220, 38, 38, 0.4);
    }

    .small-tag {
        font-size: 0.7rem;
        padding: 2px 6px;
        border-radius: 999px;
        border: 1px solid #1f2937;
        color: #9ca3af;
        margin-left: 6px;
    }

    .top-banner {
        display: flex;
        flex-direction: column;
        gap: 0.3rem;
    }

    .top-banner-title {
        font-size: 1.7rem;
        font-weight: 700;
    }

    .top-banner-subtitle {
        font-size: 0.9rem;
        color: #9ca3af;
    }

    .card-table-header {
        font-size: 0.85rem;
        font-weight: 600;
        color: #9ca3af;
        margin-bottom: 0.3rem;
    }

    .card-table-row {
        font-size: 0.85rem;
        padding: 4px 0;
        border-bottom: 1px solid #111827;
    }

    .card-table-row:last-child {
        border-bottom: none;
    }

    .highlight-birthday {
        color: #fbbf24;
        font-weight: 700;
    }

    .small-text {
        font-size: 0.78rem;
        color: #9ca3af;
        margin-top: 4px;
    }

    .motivational-text {
        font-size: 0.9rem;
        color: #d1d5db;
        margin-top: 0.5rem;
    }

    /* Tabela compacta */
    .dataframe tbody tr th {
        font-size: 0.8rem;
    }
    .dataframe tbody tr td {
        font-size: 0.8rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# CONSTANTES / ENDPOINTS
# ---------------------------------------------------------
BASE_URL_CORRETORES = "https://api.supremocrm.com.br/v1/corretores"


@st.cache_data(ttl=3600)
def carregar_corretores(max_pages: int = 50) -> pd.DataFrame:
    """
    Carrega corretores da API do Supremo.
    Cache de 1h para não pesar a operação.
    Aceita respostas com chaves 'data' ou 'dados'.
    """
    headers = {"Authorization": f"Bearer {TOKEN_SUPREMO}"}
    dfs = []
    pagina = 1
    total_paginas = None

    while True:
        params = {"pagina": pagina}
        try:
            resp = requests.get(
                BASE_URL_CORRETORES,
                headers=headers,
                params=params,
                timeout=30,
            )
        except Exception as e:
            st.error(f"Erro ao chamar a API de corretores: {e}")
            return pd.DataFrame()

        if resp.status_code != 200:
            corpo = resp.text
            corpo_resumido = corpo[:300] + ("..." if len(corpo) > 300 else "")
            st.error(
                f"API de corretores respondeu com status {resp.status_code}. "
                f"Detalhe (início da resposta): {corpo_resumido}"
            )
            return pd.DataFrame()

        try:
            data = resp.json()
        except Exception as e:
            st.error(f"Não foi possível interpretar o JSON da API de corretores: {e}")
            return pd.DataFrame()

        # Estruturas possíveis:
        # { "data": [...], "current_page": 1, "last_page": X, ... }
        # { "dados": [...], "paginaAtual": 1, "totalPaginas": X, ... }
        # [ {...}, {...} ]
        if isinstance(data, dict):
            if "data" in data:
                registros = data.get("data", [])
            elif "dados" in data:
                registros = data.get("dados", [])
            else:
                registros = []

            df_page = pd.DataFrame(registros)

            total_paginas = (
                data.get("last_page")
                or data.get("totalPaginas")
                or data.get("total_paginas")
                or pagina
            )
        elif isinstance(data, list):
            df_page = pd.DataFrame(data)
            total_paginas = pagina
        else:
            df_page = pd.DataFrame()

        if df_page.empty:
            break

        dfs.append(df_page)

        if total_paginas is None:
            pagina += 1
        else:
            if pagina >= total_paginas:
                break
            pagina += 1

        if pagina > max_pages:
            break

    if not dfs:
        return pd.DataFrame()

    df_all = pd.concat(dfs, ignore_index=True)

    # ---- Nome normalizado ----
    if "nome" in df_all.columns:
        df_all["NOME_CRM"] = (
            df_all["nome"]
            .fillna("NÃO INFORMADO")
            .astype(str)
            .str.upper()
            .str.strip()
        )
    else:
        df_all["NOME_CRM"] = "NÃO INFORMADO"

    # ---- Status normalizado ----
    # Se existir coluna "status", mapeia; se não existir, considera todo mundo ATIVO.
    if "status" in df_all.columns:
        def map_status(x):
            s = str(x).strip().upper()
            if s in ("1", "SIM", "TRUE", "ATIVO"):
                return "ATIVO"
            return "INATIVO"

        df_all["STATUS_CRM"] = df_all["status"].apply(map_status)
    else:
        df_all["STATUS_CRM"] = "ATIVO"

    # ---- Telefone ----
    if "ddd" in df_all.columns and "telefone" in df_all.columns:
        df_all["TELEFONE_CRM"] = (
            df_all["ddd"].fillna("").astype(str).str.strip()
            + " "
            + df_all["telefone"].fillna("").astype(str).str.strip()
        ).str.strip()
    else:
        df_all["TELEFONE_CRM"] = ""

    # ---- Aniversário ----
    if "aniversario" in df_all.columns:
        df_all["ANIVERSARIO_RAW"] = df_all["aniversario"].replace(
            ["0000-00-00", "", None], pd.NA
        )
        df_all["ANIVERSARIO_DATE"] = pd.to_datetime(
            df_all["ANIVERSARIO_RAW"], errors="coerce"
        ).dt.date
    else:
        df_all["ANIVERSARIO_DATE"] = pd.NaT

    return df_all


def limpar_para_date(serie) -> pd.Series:
    dt = pd.to_datetime(serie, errors="coerce")
    return dt.dt.date


# ---------------------------------------------------------
# CARREGAR BASES
# ---------------------------------------------------------
with st.spinner("Carregando bases (planilha + CRM)..."):
    df = carregar_dados_planilha()
    try:
        df_corretores_crm = carregar_corretores()
    except Exception:
        df_corretores_crm = pd.DataFrame()

    try:
        df_leads = carregar_leads_direto(limit=2000, max_pages=50)
    except Exception:
        df_leads = pd.DataFrame()

# ---------------------------------------------------------
# AJUSTAR COLUNAS DA PLANILHA
# ---------------------------------------------------------
if df is None or df.empty:
    st.error("Base da planilha está vazia ou não foi carregada.")
    st.stop()

df_planilha = df.copy()

# Garantir colunas básicas
for col in ["DIA", "CORRETOR", "EQUIPE", "STATUS_BASE"]:
    if col not in df_planilha.columns:
        df_planilha[col] = np.nan

df_planilha["DIA"] = limpar_para_date(df_planilha["DIA"])

df_planilha["CORRETOR_NORM"] = (
    df_planilha["CORRETOR"]
    .fillna("NÃO INFORMADO")
    .astype(str)
    .str.upper()
    .str.strip()
)

df_planilha["EQUIPE_NORM"] = (
    df_planilha["EQUIPE"]
    .fillna("NÃO INFORMADO")
    .astype(str)
    .str.upper()
    .str.strip()
)

df_planilha["STATUS_BASE_NORM"] = (
    df_planilha["STATUS_BASE"]
    .fillna("")
    .astype(str)
    .str.upper()
)

# ---------------------------------------------------------
# AJUSTAR LEADS (CAPTURA DIRETO SUPREMO)
# ---------------------------------------------------------
if not df_leads.empty:
    if "data_captura" in df_leads.columns:
        df_leads["data_captura"] = pd.to_datetime(
            df_leads["data_captura"], errors="coerce"
        )
        df_leads["DATA_CAPTURA_DATE"] = df_leads["data_captura"].dt.date
    else:
        df_leads["DATA_CAPTURA_DATE"] = pd.NaT

    if "nome_corretor" in df_leads.columns:
        df_leads["NOME_CORRETOR_LEAD"] = (
            df_leads["nome_corretor"]
            .fillna("NÃO INFORMADO")
            .astype(str)
            .str.upper()
            .str.strip()
        )
    else:
        df_leads["NOME_CORRETOR_LEAD"] = "NÃO INFORMADO"
else:
    df_leads = pd.DataFrame(
        columns=["DATA_CAPTURA_DATE", "NOME_CORRETOR_LEAD"]
    )

# ---------------------------------------------------------
# NORMALIZAR CORRETORES DO CRM
# ---------------------------------------------------------
if df_corretores_crm is not None and not df_corretores_crm.empty:
    df_corretores_crm["NOME_CRM_BASE"] = (
        df_corretores_crm["NOME_CRM"]
        .fillna("NÃO INFORMADO")
        .astype(str)
        .str.upper()
        .str.strip()
    )
else:
    df_corretores_crm = pd.DataFrame(
        columns=[
            "id",
            "NOME_CRM",
            "NOME_CRM_BASE",
            "STATUS_CRM",
            "TELEFONE_CRM",
            "ANIVERSARIO_DATE",
        ]
    )

# ---------------------------------------------------------
# PERÍODO PADRÃO (ULTIMOS 60 DIAS)
# ---------------------------------------------------------
hoje = date.today()
data_ini_padrao = hoje - timedelta(days=60)
data_fim_padrao = hoje

with st.sidebar:
    st.markdown("### Filtros da visão de corretores")

    data_ini = st.date_input(
        "Período inicial",
        value=data_ini_padrao,
        min_value=hoje - timedelta(days=365),
        max_value=hoje,
    )
    data_fim = st.date_input(
        "Período final",
        value=data_fim_padrao,
        min_value=data_ini,
        max_value=hoje,
    )

    if data_ini > data_fim:
        st.error("Data inicial não pode ser maior que a data final.")
        st.stop()

    # Filtros de equipe / corretor
    equipes_disponiveis = (
        df_planilha["EQUIPE_NORM"].dropna().sort_values().unique().tolist()
    )
    equipes_disponiveis = [e for e in equipes_disponiveis if e != "NÃO INFORMADO"]

    equipe_selecionada = st.selectbox(
        "Filtrar por equipe (planilha)",
        options=["TODAS"] + equipes_disponiveis,
        index=0,
    )

    # Lista de corretores
    corretores_disponiveis = (
        df_planilha["CORRETOR_NORM"].dropna().sort_values().unique().tolist()
    )
    corretores_disponiveis = [c for c in corretores_disponiveis if c != "NÃO INFORMADO"]

    corretor_selecionado = st.selectbox(
        "Filtrar por corretor (planilha)",
        options=["TODOS"] + corretores_disponiveis,
        index=0,
    )

# ---------------------------------------------------------
# FILTRAR BASES PELO PERÍODO
# ---------------------------------------------------------
mask_periodo = (df_planilha["DIA"] >= data_ini) & (df_planilha["DIA"] <= data_fim)
df_plan_periodo = df_planilha.loc[mask_periodo].copy()

if equipe_selecionada != "TODAS":
    df_plan_periodo = df_plan_periodo[
        df_plan_periodo["EQUIPE_NORM"] == equipe_selecionada
    ]

if corretor_selecionado != "TODOS":
    df_plan_periodo = df_plan_periodo[
        df_plan_periodo["CORRETOR_NORM"] == corretor_selecionado
    ]

# ---------------------------------------------------------
# CABEÇALHO
# ---------------------------------------------------------
col_header_left, col_header_right = st.columns([3, 1])

with col_header_left:
    st.markdown(
        f"""
        <div class="top-banner">
            <div class="top-banner-title">
                🧑‍💼 Corretores – Visão Geral
            </div>
            <p class="top-banner-subtitle">
                Período: <strong>{data_ini.strftime('%d/%m/%Y')}</strong> até
                <strong>{data_fim.strftime('%d/%m/%Y')}</strong> • 
                Força de vendas integrada CRM + Planilha.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_header_right:
    try:
        st.image("logo_mr.png", use_container_width=True)
    except Exception:
        pass

st.markdown(
    """
    <p class="motivational-text">
        <strong>Ninguém é tão bom quanto todos nós juntos!</strong> 🤝✨<br>
        Aqui você enxerga quem está jogando o jogo de verdade: CRM, leads, análises e vendas.
    </p>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# INDICADORES GERAIS (PERÍODO)
# ---------------------------------------------------------
df_rank_base = df_plan_periodo.copy()

# Contagem de análises, aprovações, vendas
if "STATUS_BASE_NORM" not in df_rank_base.columns:
    df_rank_base["STATUS_BASE_NORM"] = ""

df_rank_base["IS_ANALISE"] = df_rank_base["STATUS_BASE_NORM"].isin(
    ["EM ANÁLISE", "REANÁLISE"]
)
df_rank_base["IS_APROV"] = df_rank_base["STATUS_BASE_NORM"].str.contains(
    "APROV", na=False
)

# ---------- REGRAS DE VENDA (DEDUP POR CLIENTE) ----------
# inicializa sem venda
df_rank_base["IS_VENDA"] = False

# tenta descobrir coluna de cliente
cliente_col = None
for c in df_rank_base.columns:
    nome_c = str(c).upper()
    if nome_c in ("CLIENTE", "NOME_CLIENTE", "CLIENTE_NOME"):
        cliente_col = c
        break

# linhas com algum status de venda
mask_venda_status = df_rank_base["STATUS_BASE_NORM"].str.contains(
    "VENDA", na=False
) | (df_rank_base["STATUS_BASE_NORM"] == "VENDIDO")

if cliente_col is not None and mask_venda_status.any():
    df_v = df_rank_base.loc[mask_venda_status].copy()
    df_v["CLIENTE_BASE"] = (
        df_v[cliente_col]
        .fillna("SEM CLIENTE")
        .astype(str)
        .str.upper()
        .str.strip()
    )

    if "DIA" in df_v.columns:
        df_v = df_v.sort_values("DIA")
        idx_last = df_v.groupby("CLIENTE_BASE")["DIA"].idxmax()
    else:
        # se por algum motivo não tiver DIA, considera todas
        idx_last = df_v.index

    df_rank_base.loc[idx_last, "IS_VENDA"] = True
else:
    # fallback: qualquer linha com VENDA conta
    df_rank_base["IS_VENDA"] = mask_venda_status

# transforma flags em int pra somar
df_rank_base["IS_ANALISE"] = df_rank_base["IS_ANALISE"].fillna(False).astype(int)
df_rank_base["IS_APROV"] = df_rank_base["IS_APROV"].fillna(False).astype(int)
df_rank_base["IS_VENDA"] = df_rank_base["IS_VENDA"].fillna(False).astype(int)

# VGV apenas das linhas marcadas como venda (dedupadas)
if "VGV" in df_rank_base.columns:
    df_rank_base["VGV_VENDA"] = np.where(
        df_rank_base["IS_VENDA"] == 1, df_rank_base["VGV"], 0.0
    )
else:
    df_rank_base["VGV_VENDA"] = 0.0

total_analises = int(df_rank_base["IS_ANALISE"].sum())
total_aprov = int(df_rank_base["IS_APROV"].sum())
total_vendas = int(df_rank_base["IS_VENDA"].sum())

# Corretores que tiveram qualquer movimento
corretores_ativos_periodo = (
    df_rank_base.loc[
        df_rank_base["STATUS_BASE_NORM"].notna()
        & (df_rank_base["STATUS_BASE_NORM"] != "")
    ]["CORRETOR_NORM"]
    .nunique()
)

# Leads capturados por corretor no período
if not df_leads.empty:
    mask_leads_periodo = (
        (df_leads["DATA_CAPTURA_DATE"] >= data_ini)
        & (df_leads["DATA_CAPTURA_DATE"] <= data_fim)
    )
    df_leads_periodo = df_leads.loc[mask_leads_periodo].copy()
else:
    df_leads_periodo = pd.DataFrame(columns=df_leads.columns)

total_leads_periodo = len(df_leads_periodo)

# Corretores cadastrados no CRM (ativos)
df_corretores_crm_ativos = df_corretores_crm[
    df_corretores_crm["STATUS_CRM"] == "ATIVO"
].copy()

qtde_corretores_crm_ativos = len(df_corretores_crm_ativos)

col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.markdown('<div class="metric-label">Corretores ativos no CRM</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-value">{qtde_corretores_crm_ativos}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="metric-help">Profissionais ativos cadastrados no Supremo.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with col_m2:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.markdown('<div class="metric-label">Corretores com movimento no período</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-value">{corretores_ativos_periodo}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="metric-help">Corretores que tiveram pelo menos uma movimentação na base.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with col_m3:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.markdown('<div class="metric-label">Leads capturados no período</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-value">{total_leads_periodo}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="metric-help">Leads que entraram direto via API do Supremo.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with col_m4:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.markdown('<div class="metric-label">Análises / Aprovações / Vendas</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="metric-value">{total_analises} / {total_aprov} / {total_vendas}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="metric-help">Volume do período com base na planilha.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# PAINEL DE CORRETORES (CRM + PLANILHA + LEADS)
# ---------------------------------------------------------
st.markdown("### 📊 Painel de Corretores  ", unsafe_allow_html=True)
st.caption("Uma linha por corretor: CRM, equipe, leads, análises, aprovações, vendas, VGV e dias sem movimento.")

# Agrupar base da planilha por corretor
agrup_cols = ["CORRETOR_NORM", "EQUIPE_NORM"]

df_rank = (
    df_rank_base.groupby(agrup_cols, dropna=False)
    .agg(
        ANALISES=("IS_ANALISE", "sum"),
        APROVACOES=("IS_APROV", "sum"),
        VENDAS=("IS_VENDA", "sum"),
        DIAS_SEM_MOV=("DIA", lambda x: (hoje - x.max()).days if len(x.dropna()) > 0 else -1),
        VGV=("VGV_VENDA", "sum"),
    )
    .reset_index()
)

# Tratar VGV caso não exista na base original
if "VGV" not in df_rank_base.columns:
    df_rank["VGV"] = 0.0

# Leads por corretor (captura API)
if not df_leads_periodo.empty:
    df_leads_corr = (
        df_leads_periodo.groupby("NOME_CORRETOR_LEAD")
        .size()
        .reset_index(name="LEADS")
    )
else:
    df_leads_corr = pd.DataFrame(columns=["NOME_CORRETOR_LEAD", "LEADS"])

# Merge com corretores do CRM (apenas ativos)
df_corr = df_corretores_crm_ativos[
    ["id", "NOME_CRM_BASE", "NOME_CRM", "TELEFONE_CRM", "ANIVERSARIO_DATE"]
].rename(
    columns={
        "id": "ID_CRM",
        "NOME_CRM_BASE": "CORRETOR_NORM",
        "NOME_CRM": "NOME_CRM_VISUAL",
    }
)

df_merge = pd.merge(
    df_corr,
    df_rank,
    on="CORRETOR_NORM",
    how="left",
)

df_merge = pd.merge(
    df_merge,
    df_leads_corr,
    left_on="CORRETOR_NORM",
    right_on="NOME_CORRETOR_LEAD",
    how="left",
)

df_merge["LEADS"] = df_merge["LEADS"].fillna(0).astype(int)

# Garantir numéricos
for col in ["ANALISES", "APROVACOES", "VENDAS"]:
    if col in df_merge.columns:
        df_merge[col] = df_merge[col].fillna(0).astype(int)
    else:
        df_merge[col] = 0

if "VGV" in df_merge.columns:
    df_merge["VGV"] = df_merge["VGV"].fillna(0.0).astype(float)
else:
    df_merge["VGV"] = 0.0

df_merge["DIAS_SEM_MOV"] = df_merge["DIAS_SEM_MOV"].fillna(-1).astype(int)

# Ordenar por VGV / vendas / aprovações
df_merge = df_merge.sort_values(
    by=["VENDAS", "APROVACOES", "ANALISES", "LEADS"],
    ascending=[False, False, False, False],
)

df_tabela = pd.DataFrame()

df_tabela["ID CRM"] = df_merge["ID_CRM"].fillna("").astype(str)
df_tabela["Corretor (CRM)"] = df_merge["NOME_CRM_VISUAL"].fillna("NÃO INFORMADO")
df_tabela["Corretor (planilha)"] = df_merge["CORRETOR_NORM"].fillna("NÃO INFORMADO")
df_tabela["Equipe (planilha)"] = df_merge["EQUIPE_NORM"].fillna("NÃO INFORMADO")
df_tabela["Telefone (CRM)"] = df_merge["TELEFONE_CRM"].fillna("")

# Aniversário + destaque de mês
mes_atual = hoje.month

def formatar_aniversario(d):
    if pd.isna(d):
        return "—"
    try:
        dt = pd.to_datetime(d)
    except Exception:
        return "—"
    if dt.month == mes_atual:
        return f"🎂 {dt.strftime('%d/%m')}"
    return dt.strftime("%d/%m")

df_tabela["Aniversário"] = df_merge["ANIVERSARIO_DATE"].apply(formatar_aniversario)

df_tabela["Leads"] = df_merge["LEADS"]
df_tabela["Análises"] = df_merge["ANALISES"]
df_tabela["Aprovações"] = df_merge["APROVACOES"]
df_tabela["Vendas"] = df_merge["VENDAS"]
df_tabela["VGV"] = df_merge["VGV"].round(2)
df_tabela["Dias sem mov."] = df_merge["DIAS_SEM_MOV"]

st.dataframe(
    df_tabela,
    use_container_width=True,
    hide_index=True,
)

# ---------------------------------------------------------
# ALERTAS INTELIGENTES
# ---------------------------------------------------------
st.markdown("### 🔔 Alertas Inteligentes  ")
st.caption("Onde focar energia")

df_alerta = df_merge.copy()

if df_alerta.empty:
    st.info("Sem dados para gerar alertas com os filtros atuais.")
else:
    # Corretores com muitos dias sem movimento
    df_alerta["DIAS_SEM_MOV"] = df_alerta["DIAS_SEM_MOV"].fillna(-1).astype(int)
    df_sem_mov = df_alerta[df_alerta["DIAS_SEM_MOV"] >= 7].copy()
    df_sem_mov = df_sem_mov.sort_values("DIAS_SEM_MOV", ascending=False)

    # Corretores com muitos leads e pouca produção
    df_alerta["LEADS"] = df_alerta["LEADS"].fillna(0).astype(int)
    df_alerta["ANALISES"] = df_alerta["ANALISES"].fillna(0).astype(int)
    df_alerta["APROVACOES"] = df_alerta["APROVACOES"].fillna(0).astype(int)
    df_alerta["VENDAS"] = df_alerta["VENDAS"].fillna(0).astype(int)

    cond_pouca_producao = (
        (df_alerta["LEADS"] >= 10)
        & (df_alerta["ANALISES"] == 0)
        & (df_alerta["VENDAS"] == 0)
    )

    df_pouca_producao = df_alerta[cond_pouca_producao].copy()

    col_a1, col_a2 = st.columns(2)

    with col_a1:
        st.markdown("#### ⏰ Corretores sem movimento (7+ dias)")
        if df_sem_mov.empty:
            st.write("Nenhum corretor com mais de 7 dias sem movimentação.")
        else:
            cols_view = [
                "NOME_CRM_VISUAL",
                "CORRETOR_NORM",
                "EQUIPE_NORM",
                "DIAS_SEM_MOV",
                "LEADS",
                "ANALISES",
                "VENDAS",
            ]
            st.dataframe(
                df_sem_mov[cols_view].rename(
                    columns={
                        "NOME_CRM_VISUAL": "Corretor (CRM)",
                        "CORRETOR_NORM": "Corretor (planilha)",
                        "EQUIPE_NORM": "Equipe",
                        "DIAS_SEM_MOV": "Dias sem mov.",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

    with col_a2:
        st.markdown("#### ⚠️ Corretores com leads, mas sem produção")
        if df_pouca_producao.empty:
            st.write("Nenhum corretor com muitos leads e pouca produção.")
        else:
            cols_view2 = [
                "NOME_CRM_VISUAL",
                "CORRETOR_NORM",
                "EQUIPE_NORM",
                "LEADS",
                "ANALISES",
                "APROVACOES",
                "VENDAS",
            ]
            st.dataframe(
                df_pouca_producao[cols_view2].rename(
                    columns={
                        "NOME_CRM_VISUAL": "Corretor (CRM)",
                        "CORRETOR_NORM": "Corretor (planilha)",
                        "EQUIPE_NORM": "Equipe",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

# ---------------------------------------------------------
# RANKINGS RÁPIDOS
# ---------------------------------------------------------
st.markdown("### 🏅 Rankings de Corretores  ")
st.caption("Produção no período")

if df_merge.empty:
    st.info("Sem dados para montar rankings com os filtros atuais.")
else:
    df_rank_view = df_merge.copy()

    col_r1, col_r2, col_r3 = st.columns(3)

    with col_r1:
        st.markdown("#### 🔥 Top 5 Vendas")
        df_top_vendas = (
            df_rank_view.sort_values("VENDAS", ascending=False)
            .head(5)[["NOME_CRM_VISUAL", "CORRETOR_NORM", "EQUIPE_NORM", "VENDAS"]]
        )
        st.dataframe(
            df_top_vendas.rename(
                columns={
                    "NOME_CRM_VISUAL": "Corretor (CRM)",
                    "CORRETOR_NORM": "Corretor (planilha)",
                    "EQUIPE_NORM": "Equipe",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    with col_r2:
        st.markdown("#### 📈 Top 5 Aprovações")
        df_top_aprov = (
            df_rank_view.sort_values("APROVACOES", ascending=False)
            .head(5)[["NOME_CRM_VISUAL", "CORRETOR_NORM", "EQUIPE_NORM", "APROVACOES"]]
        )
        st.dataframe(
            df_top_aprov.rename(
                columns={
                    "NOME_CRM_VISUAL": "Corretor (CRM)",
                    "CORRETOR_NORM": "Corretor (planilha)",
                    "EQUIPE_NORM": "Equipe",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    with col_r3:
        st.markdown("#### 🧲 Top 5 Leads (CRM)")
        df_top_leads = (
            df_rank_view.sort_values("LEADS", ascending=False)
            .head(5)[["NOME_CRM_VISUAL", "CORRETOR_NORM", "EQUIPE_NORM", "LEADS"]]
        )
        st.dataframe(
            df_top_leads.rename(
                columns={
                    "NOME_CRM_VISUAL": "Corretor (CRM)",
                    "CORRETOR_NORM": "Corretor (planilha)",
                    "EQUIPE_NORM": "Equipe",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

st.caption(
    "Painel integrado MR Imóveis • Corretores – Visão Geral • CRM + Planilha + Leads"
)
