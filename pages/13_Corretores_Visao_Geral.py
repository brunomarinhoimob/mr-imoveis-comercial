import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import date, datetime, timedelta

from app_dashboard import carregar_dados_planilha
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
    .metric-card {
        padding: 1rem 1.3rem;
        border-radius: 0.8rem;
        background: #111827;
        border: 1px solid #1f2933;
        box-shadow: 0 0 15px rgba(0,0,0,0.4);
    }
    .metric-title {
        font-size: 0.8rem;
        font-weight: 600;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        margin-top: 0.2rem;
        color: #f9fafb;
    }
    .metric-help {
        font-size: 0.7rem;
        color: #6b7280;
        margin-top: 0.2rem;
    }

    .top-banner {
        background: linear-gradient(90deg, #111827, #111827, #1f2937);
        padding: 1.2rem 1.4rem;
        border-radius: 0.9rem;
        border: 1px solid #1f2937;
        margin-bottom: 1rem;
    }

    .top-banner-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #f9fafb;
        margin-bottom: 0.3rem;
    }

    .top-banner-subtitle {
        font-size: 0.9rem;
        color: #9ca3af;
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


# ---------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------
def limpar_para_date(col_serie):
    """Converte uma série em datetime.date, tratando erros."""
    if col_serie is None:
        return pd.NaT
    s = pd.to_datetime(col_serie, errors="coerce")
    return s.dt.date


@st.cache_data(ttl=3600, show_spinner=False)
def carregar_corretores(limit_por_pagina: int = 100, max_pages: int = 10) -> pd.DataFrame:
    """
    Carrega os corretores do Supremo CRM usando paginação.
    Normaliza as colunas principais: nome, status, telefone, aniversário.
    """
    if not TOKEN_SUPREMO:
        return pd.DataFrame()

    headers = {"Authorization": f"Bearer {TOKEN_SUPREMO}"}
    dfs = []

    for pagina in range(1, max_pages + 1):
        params = {
            "pagina": pagina,
            "limit": limit_por_pagina,
        }
        try:
            resp = requests.get(BASE_URL_CORRETORES, headers=headers, params=params, timeout=15)
        except Exception:
            break

        if resp.status_code != 200:
            break

        try:
            data = resp.json()
        except Exception:
            break

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

        if pagina >= total_paginas:
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

    df_all["NOME_CRM_BASE"] = df_all["NOME_CRM"]

    # ---- Status (ativo / inativo) ----
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

    return df_all[
        [
            "id",
            "NOME_CRM",
            "NOME_CRM_BASE",
            "STATUS_CRM",
            "TELEFONE_CRM",
            "ANIVERSARIO_DATE",
        ]
    ].copy()


# ---------------------------------------------------------
# CARREGAR BASES (PLANILHA, CORRETORES, LEADS)
# ---------------------------------------------------------
with st.spinner("Carregando dados de corretores e planilha..."):
    df = carregar_dados_planilha()

    try:
        df_corretores_crm = carregar_corretores()
    except Exception:
        df_corretores_crm = pd.DataFrame()

    # Define lista de corretores ATIVOS (nome normalizado) para uso em toda a página
    if df_corretores_crm is not None and not df_corretores_crm.empty:
        corretores_ativos_norm = (
            df_corretores_crm.loc[
                df_corretores_crm["STATUS_CRM"] == "ATIVO", "NOME_CRM_BASE"
            ]
            .dropna()
            .astype(str)
            .str.upper()
            .str.strip()
            .unique()
            .tolist()
        )
    else:
        corretores_ativos_norm = []

    # df_leads já carregado no app principal (com colunas normalizadas)
    df_leads = st.session_state.get("df_leads", pd.DataFrame())

# ---------------------------------------------------------
# AJUSTAR COLUNAS DA PLANILHA
# ---------------------------------------------------------
if df is None or df.empty:
    st.error("Base da planilha está vazia ou não foi carregada.")
    st.stop()

df_planilha = df.copy()

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
    .fillna("SEM EQUIPE")
    .astype(str)
    .str.upper()
    .str.strip()
)

df_planilha["STATUS_BASE_NORM"] = (
    df_planilha["STATUS_BASE"]
    .fillna("")
    .astype(str)
    .str.upper()
    .str.strip()
)

# ---------------------------------------------------------
# AJUSTAR LEADS (USANDO MESMA LÓGICA DO FUNIL IMOBILIÁRIA)
# ---------------------------------------------------------
if not df_leads.empty:
    # Garante que temos data_captura_date
    if "data_captura_date" not in df_leads.columns:
        if "data_captura" in df_leads.columns:
            df_leads["data_captura"] = pd.to_datetime(
                df_leads["data_captura"], errors="coerce"
            )
            df_leads["data_captura_date"] = df_leads["data_captura"].dt.date
        else:
            df_leads["data_captura_date"] = pd.NaT

    # Garante nome do corretor normalizado
    if "nome_corretor_norm" not in df_leads.columns:
        if "nome_corretor" in df_leads.columns:
            df_leads["nome_corretor_norm"] = (
                df_leads["nome_corretor"]
                .fillna("NÃO INFORMADO")
                .astype(str)
                .str.upper()
                .str.strip()
            )
        else:
            df_leads["nome_corretor_norm"] = "NÃO INFORMADO"

    # Garante equipe normalizada (se existir)
    if "equipe_lead_norm" not in df_leads.columns:
        if "nome_equipe" in df_leads.columns:
            df_leads["equipe_lead_norm"] = (
                df_leads["nome_equipe"]
                .fillna("SEM EQUIPE")
                .astype(str)
                .str.upper()
                .str.strip()
            )
        else:
            df_leads["equipe_lead_norm"] = "SEM EQUIPE"

else:
    df_leads = pd.DataFrame(
        columns=["data_captura_date", "nome_corretor_norm", "equipe_lead_norm"]
    )

# ---------------------------------------------------------
# SE NÃO TIVERMOS CRMs, CRIA UMA BASE VAZIA
# ---------------------------------------------------------
if df_corretores_crm is None or df_corretores_crm.empty:
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
# PERÍODO PADRÃO (ÚLTIMOS 60 DIAS)
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
        min_value=hoje - timedelta(days=365),
        max_value=hoje,
    )

    if data_ini > data_fim:
        st.warning("Período inválido: data inicial maior que data final. Ajustando...")
        data_ini, data_fim = data_fim, data_ini

    equipes_disponiveis = (
        df_planilha["EQUIPE_NORM"].dropna().sort_values().unique().tolist()
    )
    equipes_disponiveis = [e for e in equipes_disponiveis if e != "SEM EQUIPE"]

    equipe_selecionada = st.selectbox(
        "Filtrar por equipe (planilha)",
        options=["TODAS"] + equipes_disponiveis,
        index=0,
    )

    corretores_disponiveis = (
        df_planilha["CORRETOR_NORM"].dropna().sort_values().unique().tolist()
    )
    # Mantém apenas corretores ativos no CRM e ignora "NÃO INFORMADO"
    corretores_disponiveis = [
        c
        for c in corretores_disponiveis
        if c != "NÃO INFORMADO"
        and (not corretores_ativos_norm or c in corretores_ativos_norm)
    ]

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
                Integrando <strong>planilha de produção</strong>, <strong>CRM</strong> e <strong>leads</strong> para enxergar a performance da equipe.
                <br>
                Período analisado: <strong>{data_ini.strftime('%d/%m/%Y')}</strong> até <strong>{data_fim.strftime('%d/%m/%Y')}</strong>.
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

# Remove corretores inativos da base de ranking (usa lista de ativos do CRM)
if corretores_ativos_norm:
    df_rank_base = df_rank_base[
        df_rank_base["CORRETOR_NORM"].isin(corretores_ativos_norm)
    ]

if "STATUS_BASE_NORM" not in df_rank_base.columns:
    df_rank_base["STATUS_BASE_NORM"] = ""

df_rank_base["IS_ANALISE"] = df_rank_base["STATUS_BASE_NORM"].isin(
    ["EM ANÁLISE", "REANÁLISE"]
)
df_rank_base["IS_APROV"] = df_rank_base["STATUS_BASE_NORM"].str.contains(
    "APROV", na=False
)

# ---------- REGRAS DE VENDA (DEDUP POR CLIENTE) ----------
df_rank_base["IS_VENDA"] = False
if "IS_VENDA" in df_rank_base.columns:
    # já existe
    pass
else:
    df_rank_base["IS_VENDA"] = False

if "TIPO_REGISTRO" in df_rank_base.columns:
    df_rank_base["TIPO_REGISTRO"] = (
        df_rank_base["TIPO_REGISTRO"]
        .fillna("")
        .astype(str)
        .str.upper()
        .str.strip()
    )
else:
    df_rank_base["TIPO_REGISTRO"] = ""

if "IS_VENDA" not in df_rank_base.columns:
    df_rank_base["IS_VENDA"] = False

# Considera venda se STATUS_BASE_NORM tiver algo de APROV + TIPO_REGISTRO contiver "VENDA"
df_rank_base["IS_VENDA"] = df_rank_base["STATUS_BASE_NORM"].str.contains(
    "APROV", na=False
) & df_rank_base["TIPO_REGISTRO"].str.contains("VENDA", na=False)

df_rank_base["VGV_VENDA"] = df_rank_base.get("VALOR_VENDA", 0.0).fillna(0.0)

# Indicadores gerais (período)
total_analises = int(df_rank_base["IS_ANALISE"].sum())
total_aprovacoes = int(df_rank_base["IS_APROV"].sum())
total_vendas = int(df_rank_base["IS_VENDA"].sum())
total_vgv = float(df_rank_base["VGV_VENDA"].sum())

qtde_corretores_com_movimento = int(
    df_rank_base.loc[
        (df_rank_base["IS_ANALISE"])
        | (df_rank_base["IS_APROV"])
        | (df_rank_base["IS_VENDA"])
    ]["CORRETOR_NORM"]
    .nunique()
)

# Leads capturados filtrados por período + equipe + corretor (igual funil)
if not df_leads.empty:
    df_leads_use = df_leads.dropna(subset=["data_captura_date"]).copy()

    mask_leads_periodo = (
        (df_leads_use["data_captura_date"] >= data_ini)
        & (df_leads_use["data_captura_date"] <= data_fim)
    )
    df_leads_periodo = df_leads_use.loc[mask_leads_periodo].copy()

    if equipe_selecionada != "TODAS" and "equipe_lead_norm" in df_leads_periodo.columns:
        df_leads_periodo = df_leads_periodo[
            df_leads_periodo["equipe_lead_norm"] == equipe_selecionada
        ]

    if (
        corretor_selecionado != "TODOS"
        and "nome_corretor_norm" in df_leads_periodo.columns
    ):
        df_leads_periodo = df_leads_periodo[
            df_leads_periodo["nome_corretor_norm"] == corretor_selecionado
        ]
else:
    df_leads_periodo = pd.DataFrame(columns=df_leads.columns)

total_leads_periodo = len(df_leads_periodo)

df_corretores_crm_ativos = df_corretores_crm[
    df_corretores_crm["STATUS_CRM"] == "ATIVO"
].copy()
qtde_corretores_crm_ativos = len(df_corretores_crm_ativos)

# ---------------------------------------------------------
# CARDS DE INDICADORES
# ---------------------------------------------------------
col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="metric-title">Corretores ativos (CRM)</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="metric-value">{qtde_corretores_crm_ativos}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="metric-help">Quantos corretores estão cadastrados como ATIVOS no CRM.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with col_m2:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="metric-title">Corretores com movimento</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="metric-value">{qtde_corretores_com_movimento}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="metric-help">Corretores que tiveram análise, aprovação ou venda no período.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with col_m3:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="metric-title">Produção do período</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="metric-value">{total_vendas} vendas</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="metric-help">{total_analises} análises • {total_aprovacoes} aprovações • VGV R$ {total_vgv:,.0f}</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with col_m4:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="metric-title">Leads capturados</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="metric-value">{total_leads_periodo}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="metric-help">Leads do período considerando equipe/corretor.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# PAINEL DE CORRETORES (TABELA PRINCIPAL)
# ---------------------------------------------------------
st.markdown("---")
st.markdown("### 📊 Painel de Corretores")
st.caption(
    "Uma linha por corretor: CRM, equipe, leads, análises, aprovações, vendas, VGV e dias sem movimento."
)

agrup_cols = ["CORRETOR_NORM", "EQUIPE_NORM"]

df_rank = (
    df_rank_base.groupby(agrup_cols, dropna=False)
    .agg(
        ANALISES=("IS_ANALISE", "sum"),
        APROVACOES=("IS_APROV", "sum"),
        VENDAS=("IS_VENDA", "sum"),
        DIAS_SEM_MOV=(
            "DIA",
            lambda x: (hoje - x.max()).days if len(x.dropna()) > 0 else -1,
        ),
        VGV=("VGV_VENDA", "sum"),
    )
    .reset_index()
)

if "VGV" not in df_rank_base.columns:
    df_rank["VGV"] = 0.0

# Leads por corretor (já filtrados por período/equipe/corretor)
if not df_leads_periodo.empty:
    df_leads_corr = (
        df_leads_periodo.groupby("nome_corretor_norm")
        .size()
        .reset_index(name="LEADS")
        .rename(columns={"nome_corretor_norm": "CORRETOR_NORM"})
    )
else:
    df_leads_corr = pd.DataFrame(columns=["CORRETOR_NORM", "LEADS"])

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
    on="CORRETOR_NORM",
    how="left",
)

df_merge["LEADS"] = df_merge["LEADS"].fillna(0).astype(int)
df_merge["ANALISES"] = df_merge["ANALISES"].fillna(0).astype(int)
df_merge["APROVACOES"] = df_merge["APROVACOES"].fillna(0).astype(int)
df_merge["VENDAS"] = df_merge["VENDAS"].fillna(0).astype(int)
df_merge["VGV"] = df_merge["VGV"].fillna(0.0)

df_merge["CONV_ANALISE_VENDA"] = np.where(
    df_merge["ANALISES"] > 0,
    (df_merge["VENDAS"] / df_merge["ANALISES"]) * 100,
    np.nan,
)

df_merge["CONV_APROV_VENDA"] = np.where(
    df_merge["APROVACOES"] > 0,
    (df_merge["VENDAS"] / df_merge["APROVACOES"]) * 100,
    np.nan,
)

df_merge["DIAS_SEM_MOV"] = df_merge["DIAS_SEM_MOV"].replace({-1: np.nan})

df_merge["ANIVERSARIO_MES"] = df_merge["ANIVERSARIO_DATE"].apply(
    lambda d: d.month == hoje.month if pd.notna(d) else False
)

df_tabela = pd.DataFrame()

if not df_merge.empty:
    df_tabela = df_merge.copy()

    df_tabela["DIAS_SEM_MOV_TXT"] = df_tabela["DIAS_SEM_MOV"].apply(
        lambda x: f"{int(x)} dias" if pd.notna(x) else "-"
    )
    df_tabela["ANIVERSARIO_TXT"] = df_tabela["ANIVERSARIO_DATE"].apply(
        lambda d: d.strftime("%d/%m") if pd.notna(d) else "-"
    )

    colunas_exibir = [
        "NOME_CRM_VISUAL",
        "CORRETOR_NORM",
        "EQUIPE_NORM",
        "LEADS",
        "ANALISES",
        "APROVACOES",
        "VENDAS",
        "VGV",
        "CONV_ANALISE_VENDA",
        "CONV_APROV_VENDA",
        "DIAS_SEM_MOV_TXT",
        "ANIVERSARIO_TXT",
    ]

    df_tabela_view = df_tabela[colunas_exibir].copy()

    df_tabela_view = df_tabela_view.rename(
        columns={
            "NOME_CRM_VISUAL": "Corretor (CRM)",
            "CORRETOR_NORM": "Corretor (planilha)",
            "EQUIPE_NORM": "Equipe",
            "LEADS": "Leads",
            "ANALISES": "Análises",
            "APROVACOES": "Aprovações",
            "VENDAS": "Vendas",
            "VGV": "VGV",
            "CONV_ANALISE_VENDA": "% Conv. Análise → Venda",
            "CONV_APROV_VENDA": "% Conv. Aprov. → Venda",
            "DIAS_SEM_MOV_TXT": "Dias sem movimento",
            "ANIVERSARIO_TXT": "Aniversário",
        }
    )

    df_tabela_view["VGV"] = df_tabela_view["VGV"].apply(
        lambda v: f"R$ {v:,.0f}".replace(",", ".")
    )
    df_tabela_view["% Conv. Análise → Venda"] = df_tabela_view[
        "% Conv. Análise → Venda"
    ].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "-")
    df_tabela_view["% Conv. Aprov. → Venda"] = df_tabela_view[
        "% Conv. Aprov. → Venda"
    ].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "-")

    st.dataframe(
        df_tabela_view,
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("Nenhum corretor com dados para exibir no período selecionado.")

# ---------------------------------------------------------
# ALERTAS E INSIGHTS
# ---------------------------------------------------------
st.markdown("---")
st.markdown("### 🚨 Alertas e Insights por Corretor")

if df_merge.empty:
    st.info("Sem dados suficientes para gerar alertas neste período.")
else:
    df_alertas = df_merge.copy()

    df_sem_mov = df_alertas[
        df_alertas["DIAS_SEM_MOV"].notna() & (df_alertas["DIAS_SEM_MOV"] >= 7)
    ].sort_values("DIAS_SEM_MOV", ascending=False)

    df_pouca_producao = df_alertas[
        (df_alertas["LEADS"] >= 5) & (df_alertas["VENDAS"] == 0)
    ].sort_values("LEADS", ascending=False)

    col_a1, col_a2 = st.columns(2)

    with col_a1:
        st.markdown("#### ⏳ Corretores há mais de 7 dias sem movimento")
        if df_sem_mov.empty:
            st.write("Nenhum corretor parado há mais de 7 dias.")
        else:
            cols_view = [
                "NOME_CRM_VISUAL",
                "CORRETOR_NORM",
                "EQUIPE_NORM",
                "DIAS_SEM_MOV",
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
                        "LEADS": "Leads",
                        "ANALISES": "Análises",
                        "APROVACOES": "Aprovações",
                        "VENDAS": "Vendas",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

# ---------------------------------------------------------
# RANKINGS RÁPIDOS
# ---------------------------------------------------------
st.markdown("---")
st.markdown("### 🏅 Rankings rápidos de corretores")

if df_merge.empty:
    st.info("Sem dados para montar rankings.")
else:
    col_r1, col_r2, col_r3 = st.columns(3)

    with col_r1:
        st.markdown("#### 🔝 Top 5 – Vendas")
        df_top_vendas = df_merge.sort_values("VENDAS", ascending=False).head(5)
        st.dataframe(
            df_top_vendas[["NOME_CRM_VISUAL", "CORRETOR_NORM", "VENDAS"]].rename(
                columns={
                    "NOME_CRM_VISUAL": "Corretor (CRM)",
                    "CORRETOR_NORM": "Corretor (planilha)",
                    "VENDAS": "Vendas",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    with col_r2:
        st.markdown("#### 💰 Top 5 – VGV")
        df_top_vgv = df_merge.sort_values("VGV", ascending=False).head(5)
        df_top_vgv_view = df_top_vgv[
            ["NOME_CRM_VISUAL", "CORRETOR_NORM", "VGV"]
        ].copy()
        df_top_vgv_view["VGV"] = df_top_vgv_view["VGV"].apply(
            lambda v: f"R$ {v:,.0f}".replace(",", ".")
        )
        st.dataframe(
            df_top_vgv_view.rename(
                columns={
                    "NOME_CRM_VISUAL": "Corretor (CRM)",
                    "CORRETOR_NORM": "Corretor (planilha)",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    with col_r3:
        st.markdown("#### 📈 Top 5 – Conversão Análises → Venda (mín. 5 análises)")
        df_conv = df_merge[df_merge["ANALISES"] >= 5].copy()
        df_conv = df_conv.sort_values("CONV_ANALISE_VENDA", ascending=False).head(5)
        df_conv_view = df_conv[
            ["NOME_CRM_VISUAL", "CORRETOR_NORM", "CONV_ANALISE_VENDA"]
        ].copy()
        df_conv_view["CONV_ANALISE_VENDA"] = df_conv_view[
            "CONV_ANALISE_VENDA"
        ].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "-")

        st.dataframe(
            df_conv_view.rename(
                columns={
                    "NOME_CRM_VISUAL": "Corretor (CRM)",
                    "CORRETOR_NORM": "Corretor (planilha)",
                    "CONV_ANALISE_VENDA": "% Conv. Análise → Venda",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

st.caption(
    "Painel integrado MR Imóveis • Corretores – Visão Geral • CRM + Planilha + Leads"
)
