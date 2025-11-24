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
        color: #f5f5f5;
    }
    section[data-testid="stSidebar"] {
        background: #111827;
        border-right: 1px solid #1f2937;
    }
    .top-banner {
        background: linear-gradient(90deg, #111827, #1f2937);
        padding: 18px 24px;
        border-radius: 20px;
        box-shadow: 0 18px 40px rgba(0,0,0,0.6);
        margin-bottom: 1.5rem;
        border: 1px solid #1f2937;
    }
    .top-banner-title {
        font-size: 1.6rem;
        font-weight: 700;
        margin: 0;
    }
    .top-banner-subtitle {
        font-size: 0.95rem;
        color: #9ca3af;
        margin-top: 4px;
        margin-bottom: 0;
    }
    .metric-card {
        background: #0b1120;
        border-radius: 16px;
        padding: 14px 16px;
        border: 1px solid #1f2937;
        box-shadow: 0 12px 30px rgba(0,0,0,0.65);
    }
    .metric-label {
        font-size: 0.8rem;
        color: #9ca3af;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 1.4rem;
        font-weight: 700;
    }
    .metric-help {
        font-size: 0.7rem;
        color: #6b7280;
    }
    .section-title {
        font-size: 1.1rem;
        font-weight: 600;
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
    }
    .section-sub {
        font-size: 0.8rem;
        color: #9ca3af;
        margin-bottom: 0.5rem;
    }
    .kanban-column {
        background: #0b1120;
        border-radius: 16px;
        padding: 10px 10px 14px 10px;
        border: 1px solid #1f2937;
        box-shadow: 0 12px 28px rgba(0,0,0,0.55);
        min-height: 120px;
    }
    .small-pill {
        display: inline-block;
        font-size: 0.65rem;
        padding: 1px 7px;
        border-radius: 999px;
        border: 1px solid #1f2937;
        background: #020617;
        color: #e5e7eb;
    }
    .pill-positivo {
        background: rgba(22, 163, 74, 0.15);
        border-color: #16a34a;
        color: #bbf7d0;
    }
    .pill-negativo {
        background: rgba(220, 38, 38, 0.15);
        border-color: #dc2626;
        color: #fecaca;
    }
    .pill-neutro {
        background: rgba(37, 99, 235, 0.15);
        border-color: #2563eb;
        color: #bfdbfe;
    }
    .tag-aniversario {
        background: linear-gradient(90deg, #f97316, #fb7185);
        color: white;
        padding: 1px 8px;
        border-radius: 999px;
        font-size: 0.7rem;
        margin-left: 4px;
    }
    .corretor-card {
        background: #020617;
        border-radius: 16px;
        padding: 10px 14px;
        margin-bottom: 10px;
        border: 1px solid #1f2937;
        box-shadow: 0 12px 26px rgba(0,0,0,0.7);
        font-size: 0.8rem;
    }
    .corretor-nome {
        font-weight: 600;
        font-size: 0.9rem;
        margin-bottom: 2px;
    }
    .corretor-meta {
        font-size: 0.7rem;
        color: #9ca3af;
    }
    .corretor-kpis {
        margin-top: 6px;
        font-size: 0.72rem;
    }
    .corretor-kpis span {
        display: inline-block;
        margin-right: 10px;
    }
    .tabela-wrapper {
        border-radius: 16px;
        border: 1px solid #1f2937;
        box-shadow: 0 12px 30px rgba(0,0,0,0.65);
        overflow: hidden;
        background: #020617;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# TOPO DA PÁGINA
# ---------------------------------------------------------
with st.container():
    st.markdown(
        """
        <div class="top-banner">
            <div class="top-banner-title">Corretores – Visão Geral</div>
            <p class="top-banner-subtitle">
                Integração <b>Supremo CRM + planilha de produção</b> para mostrar um
                panorama completo de corretores, equipes, leads, análises, aprovações
                e vendas.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------
# PARÂMETROS GERAIS
# ---------------------------------------------------------
HOJE = date.today()

# ---------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------
def format_currency(valor: float) -> str:
    if pd.isna(valor):
        valor = 0.0
    return (
        f"R$ {valor:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def safe_div(num, den):
    if den in (0, None) or pd.isna(den):
        return 0.0
    return num / den


# ---------------------------------------------------------
# CARREGAMENTO DE DADOS
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def carregar_df_planilha():
    """
    Carrega os dados da planilha única via função do app principal.
    Essa função já retorna a base consolidada com as colunas padronizadas usadas
    nas outras páginas (ANALISE, STATUS_BASE, etc).
    """
    df = carregar_dados_planilha()
    if df is None or df.empty:
        return pd.DataFrame()
    return df.copy()


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
                timeout=20,
            )
        except Exception as e:
            st.error(f"Erro de conexão com a API de corretores: {e}")
            return pd.DataFrame()

        if resp.status_code != 200:
            try:
                corpo = resp.text
            except Exception:
                corpo = ""
            st.error(
                f"Erro ao chamar API de corretores. "
                f"Status: {resp.status_code}. Corpo: {corpo[:500]}"
            )
            return pd.DataFrame()

        try:
            data = resp.json()
        except Exception as e:
            st.error(f"Erro ao decodificar JSON da API de corretores: {e}")
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
            if pagina >= int(total_paginas) or pagina >= max_pages:
                break
            pagina += 1

    if not dfs:
        st.error("API de corretores retornou vazio (sem dados).")
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

    # Mantém apenas corretores ATIVOS
    df_all = df_all[df_all["STATUS_CRM"] == "ATIVO"].copy()

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
        def parse_aniv(x):
            try:
                s = str(x).strip()
                if not s or s in ("0000-00-00", "0000-00-00 00:00:00"):
                    return pd.NaT
                dt = pd.to_datetime(s, errors="coerce")
                return dt
            except Exception:
                return pd.NaT

        df_all["ANIVERSARIO_RAW"] = df_all["aniversario"].apply(parse_aniv)
        df_all["ANIVERSARIO_DIA"] = df_all["ANIVERSARIO_RAW"].dt.day
        df_all["ANIVERSARIO_MES"] = df_all["ANIVERSARIO_RAW"].dt.month
    else:
        df_all["ANIVERSARIO_RAW"] = pd.NaT
        df_all["ANIVERSARIO_DIA"] = np.nan
        df_all["ANIVERSARIO_MES"] = np.nan

    # ---- ID ----
    if "id" in df_all.columns:
        df_all["ID_CRM"] = df_all["id"]
    else:
        df_all["ID_CRM"] = np.nan

    # ---- Login ----
    if "login" in df_all.columns:
        df_all["LOGIN_CRM"] = (
            df_all["login"].fillna("").astype(str).str.strip()
        )
    else:
        df_all["LOGIN_CRM"] = ""

    return df_all


# ---------------------------------------------------------
# CARREGAR DADOS
# ---------------------------------------------------------
df_planilha = carregar_df_planilha()
df_corretores_crm = carregar_corretores()

if df_planilha.empty:
    st.error("Não foi possível carregar dados da planilha unificada.")
    st.stop()

if df_corretores_crm.empty:
    st.error("Não foi possível carregar dados de corretores do Supremo CRM.")
    st.stop()

# ---------------------------------------------------------
# TRATAMENTO DA PLANILHA PARA CORRETORES
# ---------------------------------------------------------
# Considera apenas linhas com ANALISE válida (removendo vazios)
df_planilha["DIA"] = pd.to_datetime(df_planilha["DIA"], errors="coerce")
df_planilha["ANO_MES"] = df_planilha["DIA"].dt.to_period("M")

# Normaliza nome do corretor da planilha
if "CORRETOR" in df_planilha.columns:
    df_planilha["CORRETOR_BASE"] = (
        df_planilha["CORRETOR"]
        .fillna("NÃO INFORMADO")
        .astype(str)
        .str.upper()
        .str.strip()
    )
else:
    df_planilha["CORRETOR_BASE"] = "NÃO INFORMADO"

# Normaliza equipe
if "EQUIPE" in df_planilha.columns:
    df_planilha["EQUIPE_BASE"] = (
        df_planilha["EQUIPE"]
        .fillna("NÃO INFORMADO")
        .astype(str)
        .str.upper()
        .str.strip()
    )
else:
    df_planilha["EQUIPE_BASE"] = "NÃO INFORMADO"

# Normaliza status do funil (já deve existir STATUS_BASE)
if "STATUS_BASE" not in df_planilha.columns:
    df_planilha["STATUS_BASE"] = ""

# ---------------------------------------------------------
# CRUZANDO CRM x PLANILHA POR NOME DO CORRETOR
# ---------------------------------------------------------
# Nomes padronizados para cruzamento
df_corretores_crm["NOME_CRM_BASE"] = (
    df_corretores_crm["NOME_CRM"]
    .fillna("NÃO INFORMADO")
    .astype(str)
    .str.upper()
    .str.strip()
)

# Faz um mapeamento de nome do corretor da planilha para nome do CRM
# (no seu cenário os nomes já estão iguais, então é 1:1)
df_corretores = df_corretores_crm.copy()

# ---------------------------------------------------------
# AGREGANDO PRODUÇÃO POR CORRETOR
# ---------------------------------------------------------
# Total de análises, aprovações, vendas, VGV etc.
def agregar_por_corretor(df_base: pd.DataFrame) -> pd.DataFrame:
    df = df_base.copy()

    # Marca flags
    df["FLAG_ANALISE"] = df["STATUS_BASE"].isin(["EM ANÁLISE", "REANÁLISE"])
    df["FLAG_APROVADO"] = df["STATUS_BASE"].eq("APROVADO")
    df["FLAG_REPROVADO"] = df["STATUS_BASE"].eq("REPROVADO")
    df["FLAG_VENDA"] = df["STATUS_BASE"].isin(["VENDA GERADA", "VENDA INFORMADA"])

    if "VGV" not in df.columns:
        df["VGV"] = 0.0

    grp = (
        df.groupby("CORRETOR_BASE")
        .agg(
            EQUIPE=("EQUIPE_BASE", lambda x: x.iloc[0] if len(x) > 0 else "NÃO INFORMADO"),
            QT_ANALISES=("FLAG_ANALISE", "sum"),
            QT_APROVADOS=("FLAG_APROVADO", "sum"),
            QT_REPROVADOS=("FLAG_REPROVADO", "sum"),
            QT_VENDAS=("FLAG_VENDA", "sum"),
            VGV_TOTAL=("VGV", "sum"),
        )
        .reset_index()
    )

    grp["CONVERSAO_ANALISE_VENDA"] = grp.apply(
        lambda row: safe_div(row["QT_VENDAS"], row["QT_ANALISES"]), axis=1
    )

    return grp


df_prod_corretor = agregar_por_corretor(df_planilha)

# ---------------------------------------------------------
# JUNÇÃO COM CRM
# ---------------------------------------------------------
df_corretor_full = pd.merge(
    df_corretores,
    df_prod_corretor,
    left_on="NOME_CRM_BASE",
    right_on="CORRETOR_BASE",
    how="left",
)

# Preenche NaN para corretores sem produção
for col in [
    "QT_ANALISES",
    "QT_APROVADOS",
    "QT_REPROVADOS",
    "QT_VENDAS",
    "VGV_TOTAL",
    "CONVERSAO_ANALISE_VENDA",
]:
    if col in df_corretor_full.columns:
        df_corretor_full[col] = df_corretor_full[col].fillna(0)

# ---------------------------------------------------------
# LEADS POR CORRETOR (via API de leads)
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def carregar_leads():
    df_leads = carregar_leads_direto(limit=2000, max_pages=50)
    if df_leads is None or df_leads.empty:
        return pd.DataFrame()

    # Normalizar nome do corretor nos leads
    possiveis_cols_corretor = ["nome_corretor", "corretor", "responsavel"]
    col_cor_lead = None
    for c in possiveis_cols_corretor:
        if c in df_leads.columns:
            col_cor_lead = c
            break

    if col_cor_lead is None:
        df_leads["CORRETOR_LEAD"] = "NÃO INFORMADO"
    else:
        df_leads["CORRETOR_LEAD"] = (
            df_leads[col_cor_lead]
            .fillna("NÃO INFORMADO")
            .astype(str)
            .str.upper()
            .str.strip()
        )

    # Data captura
    if "data_captura" in df_leads.columns:
        df_leads["DATA_CAPTURA"] = pd.to_datetime(
            df_leads["data_captura"], errors="coerce"
        )
        df_leads["DATA_CAPTURA_DATE"] = df_leads["DATA_CAPTURA"].dt.date
    else:
        df_leads["DATA_CAPTURA_DATE"] = pd.NaT

    return df_leads


df_leads = carregar_leads()

df_leads_agg = pd.DataFrame()
if not df_leads.empty:
    df_leads_agg = (
        df_leads.groupby("CORRETOR_LEAD")
        .agg(QT_LEADS=("id", "count"))
        .reset_index()
        .rename(columns={"CORRETOR_LEAD": "CORRETOR_BASE"})
    )

# Junta leads na base do corretor
df_corretor_full = pd.merge(
    df_corretor_full,
    df_leads_agg,
    on="CORRETOR_BASE",
    how="left",
)

if "QT_LEADS" in df_corretor_full.columns:
    df_corretor_full["QT_LEADS"] = df_corretor_full["QT_LEADS"].fillna(0)
else:
    df_corretor_full["QT_LEADS"] = 0

# ---------------------------------------------------------
# FILTROS NA SIDEBAR
# ---------------------------------------------------------
st.sidebar.title("Filtros – Corretores")

# Filtro por equipe
equipes = (
    df_corretor_full["EQUIPE"]
    .fillna("NÃO INFORMADO")
    .astype(str)
    .sort_values()
    .unique()
    .tolist()
)

equipe_sel = st.sidebar.selectbox(
    "Equipe:",
    options=["Todas"] + equipes,
    index=0,
)

df_filtrado = df_corretor_full.copy()
if equipe_sel != "Todas":
    df_filtrado = df_filtrado[df_filtrado["EQUIPE"] == equipe_sel]

# Filtro por corretor
corretores = (
    df_filtrado["NOME_CRM_BASE"]
    .fillna("NÃO INFORMADO")
    .astype(str)
    .sort_values()
    .unique()
    .tolist()
)

corretor_sel = st.sidebar.selectbox(
    "Corretor:",
    options=["Todos"] + corretores,
    index=0,
)

if corretor_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["NOME_CRM_BASE"] == corretor_sel]

# ---------------------------------------------------------
# KPIS GERAIS
# ---------------------------------------------------------
total_corretores = len(df_filtrado)
soma_leads = df_filtrado["QT_LEADS"].sum()
soma_analises = df_filtrado["QT_ANALISES"].sum() if "QT_ANALISES" in df_filtrado.columns else 0
soma_aprov = df_filtrado["QT_APROVADOS"].sum() if "QT_APROVADOS" in df_filtrado.columns else 0
soma_vendas = df_filtrado["QT_VENDAS"].sum() if "QT_VENDAS" in df_filtrado.columns else 0
vgv_total = df_filtrado["VGV_TOTAL"].sum() if "VGV_TOTAL" in df_filtrado.columns else 0.0

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.markdown('<div class="metric-label">Corretores ativos no CRM</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-value">{int(total_corretores)}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="metric-help">Apenas corretores com status ATIVO no Supremo.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.markdown('<div class="metric-label">Leads recebidos (visão atual)</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-value">{int(soma_leads)}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="metric-help">Total de leads atribuídos aos corretores filtrados.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with c3:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.markdown('<div class="metric-label">Análises realizadas (planilha)</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-value">{int(soma_analises)}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="metric-help">Análises (EM ANÁLISE + REANÁLISE) registradas.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with c4:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.markdown('<div class="metric-label">Vendas e VGV</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric-value">{int(soma_vendas)} vendas</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="metric-help">VGV total: {format_currency(vgv_total)}</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# SEÇÃO: PAINEL DE CORRETORES
# ---------------------------------------------------------
st.markdown('<div class="section-title">Painel de Corretores <span class="small-pill pill-neutro">CRM + Produção</span></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-sub">Uma linha por corretor: CRM, equipe, leads, análises, aprovações, vendas, VGV e dias sem movimento.</div>',
    unsafe_allow_html=True,
)

if df_filtrado.empty:
    st.info("Nenhum corretor encontrado com os filtros atuais.")
else:
    # Enriquecimentos
    df_grid = df_filtrado.copy()

    # Flag aniversário no mês corrente
    mes_atual = HOJE.month
    df_grid["ANIVERSARIO_MES_ATUAL"] = df_grid["ANIVERSARIO_MES"] == mes_atual
    df_grid["ANIVERSARIO_STR"] = df_grid["ANIVERSARIO_RAW"].dt.strftime("%d/%m").fillna("")

    # Dias sem movimentação (baseado na última data que aparece para o corretor na planilha)
    df_mov = (
        df_planilha.groupby("CORRETOR_BASE")
        .agg(ULTIMA_DATA=("DIA", "max"))
        .reset_index()
    )
    df_grid = pd.merge(
        df_grid,
        df_mov,
        on="CORRETOR_BASE",
        how="left",
    )

    df_grid["DIAS_SEM_MOV"] = (pd.to_datetime(HOJE) - pd.to_datetime(df_grid["ULTIMA_DATA"])).dt.days
    df_grid["DIAS_SEM_MOV"] = df_grid["DIAS_SEM_MOV"].fillna(-1)

    # Monta dataframe clean
    colunas_grid = [
        "ID_CRM",
        "NOME_CRM_BASE",
        "EQUIPE",
        "LOGIN_CRM",
        "TELEFONE_CRM",
        "STATUS_CRM",
        "QT_LEADS",
        "QT_ANALISES",
        "QT_APROVADOS",
        "QT_REPROVADOS",
        "QT_VENDAS",
        "VGV_TOTAL",
        "CONVERSAO_ANALISE_VENDA",
        "DIAS_SEM_MOV",
        "ANIVERSARIO_STR",
        "ANIVERSARIO_MES_ATUAL",
    ]
    colunas_existentes = [c for c in colunas_grid if c in df_grid.columns]
    df_view = df_grid[colunas_existentes].copy()

    # Ajustes de apresentação
    if "CONVERSAO_ANALISE_VENDA" in df_view.columns:
        df_view["CONVERSAO_ANALISE_VENDA"] = (
            df_view["CONVERSAO_ANALISE_VENDA"].fillna(0) * 100
        )
        df_view["CONVERSAO_ANALISE_VENDA"] = df_view["CONVERSAO_ANALISE_VENDA"].map(
            lambda x: f"{x:.1f}%"
        )

    if "VGV_TOTAL" in df_view.columns:
        df_view["VGV_TOTAL"] = df_view["VGV_TOTAL"].map(format_currency)

    if "STATUS_CRM" in df_view.columns:
        df_view["STATUS_CRM"] = df_view["STATUS_CRM"].astype(str)

    # Renomeia colunas
    rename_cols = {
        "ID_CRM": "ID",
        "NOME_CRM_BASE": "Corretor",
        "EQUIPE": "Equipe",
        "LOGIN_CRM": "Login",
        "TELEFONE_CRM": "Contato",
        "STATUS_CRM": "Status CRM",
        "QT_LEADS": "Leads",
        "QT_ANALISES": "Análises",
        "QT_APROVADOS": "Aprov.",
        "QT_REPROVADOS": "Reprov.",
        "QT_VENDAS": "Vendas",
        "VGV_TOTAL": "VGV",
        "CONVERSAO_ANALISE_VENDA": "% Conv. Análise → Venda",
        "DIAS_SEM_MOV": "Dias sem mov.",
        "ANIVERSARIO_STR": "Aniversário",
    }
    df_view = df_view.rename(columns=rename_cols)

    with st.container():
        st.markdown('<div class="tabela-wrapper">', unsafe_allow_html=True)
        st.dataframe(
            df_view,
            use_container_width=True,
            hide_index=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# SEÇÃO: ALERTAS INTELIGENTES
# ---------------------------------------------------------
st.markdown('<div class="section-title">Alertas Inteligentes <span class="small-pill pill-negativo">Onde focar energia</span></div>', unsafe_allow_html=True)

if df_filtrado.empty:
    st.info("Sem dados para gerar alertas com os filtros atuais.")
else:
    df_alerta = df_filtrado.copy()

    # Alerta 1: corretores sem leads
    sem_leads = df_alerta[df_alerta["QT_LEADS"] == 0]

    # Alerta 2: corretores com muitas análises mas zero vendas
    cond_muitas_analises = df_alerta["QT_ANALISES"] >= 10
    cond_zero_vendas = df_alerta["QT_VENDAS"] == 0
    muita_analise_sem_venda = df_alerta[cond_muitas_analises & cond_zero_vendas]

    # Alerta 3: corretores há muitos dias sem movimentação
    cond_sem_mov = df_alerta["DIAS_SEM_MOV"] >= 7
    muito_tempo_sem_mov = df_alerta[cond_sem_mov]

    if sem_leads.empty and muita_analise_sem_venda.empty and muito_tempo_sem_mov.empty:
        st.success("Sem dados para gerar alertas com os filtros atuais.")
    else:
        if not sem_leads.empty:
            st.markdown("**Corretores sem nenhum lead atribuído:**")
            st.write(
                sem_leads[["NOME_CRM_BASE", "EQUIPE", "QT_LEADS"]]
                .rename(
                    columns={
                        "NOME_CRM_BASE": "Corretor",
                        "EQUIPE": "Equipe",
                        "QT_LEADS": "Leads",
                    }
                )
                .reset_index(drop=True)
            )

        if not muita_analise_sem_venda.empty:
            st.markdown("**Corretores com muitas análises mas sem vendas:**")
            st.write(
                muita_analise_sem_venda[
                    ["NOME_CRM_BASE", "EQUIPE", "QT_ANALISES", "QT_VENDAS"]
                ]
                .rename(
                    columns={
                        "NOME_CRM_BASE": "Corretor",
                        "EQUIPE": "Equipe",
                        "QT_ANALISES": "Análises",
                        "QT_VENDAS": "Vendas",
                    }
                )
                .reset_index(drop=True)
            )

        if not muito_tempo_sem_mov.empty:
            st.markdown("**Corretores há muitos dias sem movimentação:**")
            st.write(
                muito_tempo_sem_mov[
                    ["NOME_CRM_BASE", "EQUIPE", "DIAS_SEM_MOV"]
                ]
                .rename(
                    columns={
                        "NOME_CRM_BASE": "Corretor",
                        "EQUIPE": "Equipe",
                        "DIAS_SEM_MOV": "Dias sem mov.",
                    }
                )
                .reset_index(drop=True)
            )

# ---------------------------------------------------------
# SEÇÃO: RANKINGS DE CORRETORES
# ---------------------------------------------------------
st.markdown('<div class="section-title">Rankings de Corretores <span class="small-pill pill-neutro">Produção no período</span></div>', unsafe_allow_html=True)

if df_filtrado.empty:
    st.info("Sem dados para montar rankings com os filtros atuais.")
else:
    df_rank = df_filtrado.copy()

    # Ranking por vendas
    rank_vendas = (
        df_rank.sort_values(["QT_VENDAS", "VGV_TOTAL"], ascending=False)
        .loc[:, ["NOME_CRM_BASE", "EQUIPE", "QT_VENDAS", "VGV_TOTAL"]]
        .rename(
            columns={
                "NOME_CRM_BASE": "Corretor",
                "EQUIPE": "Equipe",
                "QT_VENDAS": "Vendas",
                "VGV_TOTAL": "VGV",
            }
        )
    )
    if not rank_vendas.empty:
        rank_vendas["VGV"] = rank_vendas["VGV"].map(format_currency)

    # Ranking por análises
    rank_analises = (
        df_rank.sort_values("QT_ANALISES", ascending=False)
        .loc[:, ["NOME_CRM_BASE", "EQUIPE", "QT_ANALISES"]]
        .rename(
            columns={
                "NOME_CRM_BASE": "Corretor",
                "EQUIPE": "Equipe",
                "QT_ANALISES": "Análises",
            }
        )
    )

    # Ranking por leads
    rank_leads = (
        df_rank.sort_values("QT_LEADS", ascending=False)
        .loc[:, ["NOME_CRM_BASE", "EQUIPE", "QT_LEADS"]]
        .rename(
            columns={
                "NOME_CRM_BASE": "Corretor",
                "EQUIPE": "Equipe",
                "QT_LEADS": "Leads",
            }
        )
    )

    c_rank1, c_rank2, c_rank3 = st.columns(3)

    with c_rank1:
        st.markdown("**Top corretores por vendas (quantidade + VGV):**")
        if rank_vendas.empty:
            st.write("Sem dados.")
        else:
            st.dataframe(rank_vendas.head(10), hide_index=True, use_container_width=True)

    with c_rank2:
        st.markdown("**Top corretores por análises:**")
        if rank_analises.empty:
            st.write("Sem dados.")
        else:
            st.dataframe(rank_analises.head(10), hide_index=True, use_container_width=True)

    with c_rank3:
        st.markdown("**Top corretores por leads recebidos:**")
        if rank_leads.empty:
            st.write("Sem dados.")
        else:
            st.dataframe(rank_leads.head(10), hide_index=True, use_container_width=True)

# ---------------------------------------------------------
# RODAPÉ
# ---------------------------------------------------------
st.markdown(
    "<br><sub>Painel integrado MR Imóveis • Corretores – Visão Geral • CRM + Planilha + Leads</sub>",
    unsafe_allow_html=True,
)
