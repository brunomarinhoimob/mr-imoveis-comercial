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
# ESTILO / CSS (DARK PREMIUM)
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

    .motivational-text {
        font-size: 1rem;
        margin-bottom: 1.5rem;
        color: #e5e7eb;
    }

    .motivational-text span.number {
        font-weight: 700;
        color: #38bdf8;
    }

    .metric-card {
        background: #111827;
        padding: 16px 20px;
        border-radius: 18px;
        box-shadow: 0 14px 30px rgba(0,0,0,0.55);
        border: 1px solid #1f2937;
        text-align: left;
        margin-bottom: 1rem;
    }

    .metric-label {
        font-size: 0.85rem;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 6px;
    }

    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
    }

    .metric-helper {
        font-size: 0.8rem;
        color: #6b7280;
        margin-top: 4px;
    }

    .section-title {
        font-size: 1.1rem;
        font-weight: 600;
        margin-top: 0.5rem;
        margin-bottom: 0.4rem;
    }

    .section-subtitle {
        font-size: 0.85rem;
        color: #9ca3af;
        margin-bottom: 0.5rem;
    }

    .badge-chip {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: #1f2937;
        border-radius: 999px;
        padding: 2px 10px;
        font-size: 0.75rem;
        color: #9ca3af;
        border: 1px solid #374151;
        margin-left: 8px;
    }

    .alert-text {
        font-size: 0.85rem;
        color: #f97316;
    }

    .good-text {
        font-size: 0.85rem;
        color: #22c55e;
    }

    .small-caption {
        font-size: 0.75rem;
        color: #6b7280;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# CONSTANTES – API CORRETORES
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
            corpo_resumido = corpo[:300].replace("\n", " ").replace("\r", " ")
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
df_planilha = carregar_dados_planilha()

if df_planilha.empty:
    st.error("Erro ao carregar dados da planilha.")
    st.stop()

df_planilha["DIA"] = pd.to_datetime(df_planilha["DIA"], errors="coerce")
df_planilha["DIA_DATE"] = df_planilha["DIA"].dt.date

df_planilha["CORRETOR_MATCH"] = (
    df_planilha["CORRETOR"]
    .fillna("NÃO INFORMADO")
    .astype(str)
    .str.upper()
    .str.strip()
)
df_planilha["EQUIPE"] = (
    df_planilha["EQUIPE"]
    .fillna("NÃO INFORMADO")
    .astype(str)
    .str.upper()
    .str.strip()
)

# Leads
if "df_leads" in st.session_state:
    df_leads = st.session_state["df_leads"]
else:
    try:
        df_leads = carregar_leads_direto(limit=2000, max_pages=50)
    except Exception:
        df_leads = pd.DataFrame()

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

df_corretores = carregar_corretores()

if df_corretores.empty:
    st.error("Erro ao carregar corretores do CRM.")
    st.stop()

# ---------------------------------------------------------
# SIDEBAR – FILTROS
# ---------------------------------------------------------
st.sidebar.title("Filtros – Corretores")

dias_validos = df_planilha["DIA_DATE"].dropna()
if dias_validos.empty:
    hoje = date.today()
    data_min = hoje - timedelta(days=30)
    data_max = hoje
else:
    data_min = dias_validos.min()
    data_max = dias_validos.max()

data_ini_default = max(data_min, data_max - timedelta(days=30))

periodo = st.sidebar.date_input(
    "Período (movimentação / leads)",
    value=(data_ini_default, data_max),
    min_value=data_min,
    max_value=data_max,
)

if isinstance(periodo, tuple):
    data_ini, data_fim = periodo
else:
    data_ini, data_fim = data_ini_default, data_max

if data_ini > data_fim:
    data_ini, data_fim = data_fim, data_ini

status_opcoes = ["ATIVOS", "INATIVOS", "TODOS"]
status_sel = st.sidebar.selectbox(
    "Status no CRM",
    status_opcoes,
    index=0,
)

lista_equipes = sorted(df_planilha["EQUIPE"].dropna().unique())
equipe_sel = st.sidebar.selectbox(
    "Equipe (base planilha)",
    ["Todas"] + lista_equipes,
    index=0,
)

# Filtro por corretor (opcional)
lista_corretores_sidebar = sorted(df_corretores["NOME_CRM"].dropna().unique())
corretor_sel = st.sidebar.selectbox(
    "Corretor (opcional)",
    ["Todos"] + lista_corretores_sidebar,
    index=0,
)

st.sidebar.caption(
    "Corretores vêm do Supremo CRM. Análises, aprovações e vendas vêm da planilha."
)

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
# FILTRAR BASES PELO PERÍODO
# ---------------------------------------------------------
mask_planilha_periodo = (
    (df_planilha["DIA_DATE"] >= data_ini)
    & (df_planilha["DIA_DATE"] <= data_fim)
)
df_plan_periodo = df_planilha[mask_planilha_periodo].copy()

if not df_leads.empty:
    mask_leads_periodo = (
        (df_leads["DATA_CAPTURA_DATE"] >= data_ini)
        & (df_leads["DATA_CAPTURA_DATE"] <= data_fim)
    )
    df_leads_periodo = df_leads[mask_leads_periodo].copy()
else:
    df_leads_periodo = pd.DataFrame()

# ---------------------------------------------------------
# AGRUPAMENTOS – PLANILHA
# ---------------------------------------------------------
if df_plan_periodo.empty:
    df_plan_agg = pd.DataFrame(
        columns=[
            "CORRETOR_MATCH",
            "EQUIPE",
            "ANALISES_EM",
            "APROVACOES",
            "VENDAS",
            "VGV",
            "ULTIMA_MOV",
        ]
    )
else:
    df_plan_periodo["STATUS_BASE"] = (
        df_plan_periodo["STATUS_BASE"]
        .fillna("")
        .astype(str)
        .str.upper()
    )

    def primeira_equipe(grupo):
        serie = grupo.dropna()
        return serie.iloc[0] if not serie.empty else "NÃO INFORMADO"

    plan_group = df_plan_periodo.groupby("CORRETOR_MATCH", as_index=False).agg(
        ANALISES_EM=("STATUS_BASE", lambda s: (s == "EM ANÁLISE").sum()),
        APROVACOES=("STATUS_BASE", lambda s: (s == "APROVADO").sum()),
        VENDAS=(
            "STATUS_BASE",
            lambda s: s.isin(["VENDA GERADA", "VENDA INFORMADA"]).sum(),
        ),
        VGV=("VGV", "sum"),
        ULTIMA_MOV=("DIA_DATE", "max"),
        EQUIPE=("EQUIPE", primeira_equipe),
    )

    df_plan_agg = plan_group

# ---------------------------------------------------------
# AGRUPAMENTOS – LEADS
# ---------------------------------------------------------
if df_leads_periodo.empty:
    df_leads_agg = pd.DataFrame(
        columns=["NOME_CORRETOR_LEAD", "LEADS", "ULTIMO_LEAD"]
    )
else:
    leads_group = df_leads_periodo.groupby("NOME_CORRETOR_LEAD", as_index=False).agg(
        LEADS=("id", "count") if "id" in df_leads_periodo.columns else ("NOME_CORRETOR_LEAD", "size"),
        ULTIMO_LEAD=("DATA_CAPTURA_DATE", "max"),
    )
    df_leads_agg = leads_group

# ---------------------------------------------------------
# UNIR CORRETORES (CRM) + PLANILHA + LEADS
# ---------------------------------------------------------
df_corretores["NOME_MATCH"] = df_corretores["NOME_CRM"]

if status_sel == "ATIVOS":
    df_corretores_filtrado = df_corretores[df_corretores["STATUS_CRM"] == "ATIVO"].copy()
elif status_sel == "INATIVOS":
    df_corretores_filtrado = df_corretores[df_corretores["STATUS_CRM"] == "INATIVO"].copy()
else:
    df_corretores_filtrado = df_corretores.copy()

df_merge = df_corretores_filtrado.merge(
    df_plan_agg,
    how="left",
    left_on="NOME_MATCH",
    right_on="CORRETOR_MATCH",
)

df_merge = df_merge.merge(
    df_leads_agg,
    how="left",
    left_on="NOME_MATCH",
    right_on="NOME_CORRETOR_LEAD",
)

if equipe_sel != "Todas":
    df_merge = df_merge[df_merge["EQUIPE"] == equipe_sel]

# Filtro final por corretor (se selecionado)
if corretor_sel != "Todos":
    df_merge = df_merge[df_merge["NOME_CRM"] == corretor_sel]

for col in ["ANALISES_EM", "APROVACOES", "VENDAS", "LEADS"]:
    if col in df_merge.columns:
        df_merge[col] = df_merge[col].fillna(0).astype(int)
    else:
        df_merge[col] = 0

if "VGV" in df_merge.columns:
    df_merge["VGV"] = df_merge["VGV"].fillna(0.0).astype(float)
else:
    df_merge["VGV"] = 0.0

df_merge["ULTIMA_MOV"] = pd.to_datetime(df_merge["ULTIMA_MOV"], errors="coerce")
df_merge["ULTIMO_LEAD"] = pd.to_datetime(df_merge["ULTIMO_LEAD"], errors="coerce")

df_merge["ULTIMA_ATIVIDADE"] = df_merge[["ULTIMA_MOV", "ULTIMO_LEAD"]].max(axis=1)

hoje_dt = datetime.combine(date.today(), datetime.min.time())
df_merge["DIAS_SEM_MOV"] = (hoje_dt - df_merge["ULTIMA_ATIVIDADE"]).dt.days
df_merge.loc[df_merge["ULTIMA_ATIVIDADE"].isna(), "DIAS_SEM_MOV"] = np.nan

df_merge["TEVE_LEAD"] = df_merge["LEADS"] > 0
df_merge["TEVE_ANALISE"] = df_merge["ANALISES_EM"] > 0
df_merge["TEVE_VENDA"] = df_merge["VENDAS"] > 0

df_merge["FANTASMA"] = (
    (df_merge["STATUS_CRM"] == "ATIVO")
    & (~df_merge["TEVE_LEAD"])
    & (~df_merge["TEVE_ANALISE"])
    & (~df_merge["TEVE_VENDA"])
)

# Garante coluna de aniversário mesmo se vier vazia
if "ANIVERSARIO_DATE" not in df_merge.columns:
    df_merge["ANIVERSARIO_DATE"] = pd.NaT

# ---------------------------------------------------------
# KPIs GERAIS
# ---------------------------------------------------------
total_corretores_crm = len(df_corretores)
total_corretores_filtrados = len(df_corretores_filtrado)
total_ativos = (df_corretores["STATUS_CRM"] == "ATIVO").sum()

ativos_com_mov = (
    (df_merge["STATUS_CRM"] == "ATIVO")
    & (df_merge["TEVE_LEAD"] | df_merge["TEVE_ANALISE"] | df_merge["TEVE_VENDA"])
).sum()

fantasmas = df_merge["FANTASMA"].sum()

col_k1, col_k2, col_k3, col_k4 = st.columns(4)

with col_k1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Corretores no CRM</div>
            <div class="metric-value">{total_corretores_crm}</div>
            <div class="metric-helper">Total cadastrados (ativos + inativos)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_k2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Ativos no CRM</div>
            <div class="metric-value">{total_ativos}</div>
            <div class="metric-helper">Habilitados para receber leads</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_k3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Ativos com movimento</div>
            <div class="metric-value">{int(ativos_com_mov)}</div>
            <div class="metric-helper">Leads, análises ou vendas no período</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_k4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Ativos fantasmas</div>
            <div class="metric-value">{int(fantasmas)}</div>
            <div class="metric-helper">Sem leads, análises ou vendas no período</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.caption(
    f"Corretores considerados nesta visão (após filtros): {total_corretores_filtrados}"
)

st.markdown("---")

# ---------------------------------------------------------
# CARDS – DETALHE DO CORRETOR SELECIONADO
# ---------------------------------------------------------
if corretor_sel != "Todos" and not df_merge.empty:
    row = df_merge.iloc[0]

    nome = row["NOME_CRM"]
    status_crm = row["STATUS_CRM"]
    equipe = row.get("EQUIPE", "NÃO INFORMADO")
    telefone = row.get("TELEFONE_CRM", "")
    email = row.get("email", "")
    aniversario_date = row.get("ANIVERSARIO_DATE", pd.NaT)

    if pd.notna(aniversario_date):
        aniversario_str = aniversario_date.strftime("%d/%m")
    else:
        aniversario_str = "—"

    leads = int(row.get("LEADS", 0))
    analises = int(row.get("ANALISES_EM", 0))
    aprovacoes = int(row.get("APROVACOES", 0))
    vendas = int(row.get("VENDAS", 0))
    vgv = float(row.get("VGV", 0.0))

    ultima_mov = row.get("ULTIMA_MOV", pd.NaT)
    ultima_lead = row.get("ULTIMO_LEAD", pd.NaT)
    ultima_atividade = row.get("ULTIMA_ATIVIDADE", pd.NaT)
    dias_sem_mov = row.get("DIAS_SEM_MOV", np.nan)

    if pd.notna(ultima_mov):
        ultima_mov_str = ultima_mov.strftime("%d/%m/%Y")
    else:
        ultima_mov_str = "—"

    if pd.notna(ultima_lead):
        ultima_lead_str = ultima_lead.strftime("%d/%m/%Y")
    else:
        ultima_lead_str = "—"

    if pd.notna(ultima_atividade):
        ultima_atividade_str = ultima_atividade.strftime("%d/%m/%Y")
    else:
        ultima_atividade_str = "—"

    if pd.notna(dias_sem_mov):
        dias_sem_mov_str = f"{int(dias_sem_mov)} dias"
    else:
        dias_sem_mov_str = "—"

    # Alerta do corretor (mesma lógica da tabela)
    alerta = ""
    if status_crm == "ATIVO":
        if leads == 0 and analises == 0 and vendas == 0:
            alerta = "Fantasma: sem leads, análises ou vendas no período."
        elif leads > 0 and analises == 0:
            alerta = "Possível gargalo: leads sem análise."
        elif analises > 0 and vendas == 0:
            alerta = "Atenção: análises sem venda no período."

    st.markdown(
        """
        <div class="section-title">
            👤 Detalhe do corretor selecionado
            <span class="badge-chip">Visão 360°</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)

    # Card 1 – Dados CRM
    with c1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Dados CRM</div>
                <div class="metric-value">{nome}</div>
                <div class="metric-helper">Status: {status_crm} • Equipe: {equipe}</div>
                <p class="section-subtitle" style="margin-top:8px;">
                    📞 {telefone or '—'}<br/>
                    ✉️ {email or '—'}<br/>
                    🎂 Aniversário: {aniversario_str}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Card 2 – Produção no período
    with c2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Produção no período</div>
                <div class="metric-value">{vendas} vendas</div>
                <div class="metric-helper">VGV: R$ {vgv:,.2f}</div>
                <p class="section-subtitle" style="margin-top:8px;">
                    🧲 Leads: <strong>{leads}</strong><br/>
                    📑 Análises (EM): <strong>{analises}</strong><br/>
                    ✅ Aprovações: <strong>{aprovacoes}</strong>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Card 3 – Atividade e alerta
    with c3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Atividade</div>
                <div class="metric-value">{dias_sem_mov_str}</div>
                <div class="metric-helper">Desde a última movimentação</div>
                <p class="section-subtitle" style="margin-top:8px;">
                    Última atividade: <strong>{ultima_atividade_str}</strong><br/>
                    Última análise/venda: <strong>{ultima_mov_str}</strong><br/>
                    Último lead: <strong>{ultima_lead_str}</strong><br/>
                    {'<span class="alert-text">' + alerta + '</span>' if alerta else ''}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

# ---------------------------------------------------------
# TABELA PRINCIPAL – CORRETORES
# ---------------------------------------------------------
st.markdown(
    """
    <div class="section-title">
        📋 Painel de Corretores
        <span class="badge-chip">CRM + Produção</span>
    </div>
    <p class="section-subtitle">
        Uma linha por corretor: CRM, equipe, leads, análises, aprovações, vendas, VGV e dias sem movimento.
    </p>
    """,
    unsafe_allow_html=True,
)

if df_merge.empty:
    st.info("Nenhum corretor encontrado com os filtros atuais.")
else:
    df_tabela = pd.DataFrame()
    mes_atual = date.today().month

    def formatar_nome_corretor(row):
        nome = row["NOME_CRM"]
        aniversario = row.get("ANIVERSARIO_DATE", pd.NaT)
        try:
            if pd.notna(aniversario) and getattr(aniversario, "month", None) == mes_atual:
                return f"{nome} 🎂"
        except Exception:
            pass
        return nome

    df_tabela["Corretor (CRM)"] = df_merge.apply(formatar_nome_corretor, axis=1)
    df_tabela["Status CRM"] = df_merge["STATUS_CRM"]

    # Coluna de aniversário (dia/mês)
    df_tabela["Aniversário"] = df_merge["ANIVERSARIO_DATE"].apply(
        lambda d: d.strftime("%d/%m") if pd.notna(d) else ""
    )

    df_tabela["Equipe (planilha)"] = df_merge["EQUIPE"].fillna("NÃO INFORMADO")
    df_tabela["Leads"] = df_merge["LEADS"]
    df_tabela["Análises (só EM)"] = df_merge["ANALISES_EM"]
    df_tabela["Aprovações"] = df_merge["APROVACOES"]
    df_tabela["Vendas"] = df_merge["VENDAS"]
    df_tabela["VGV"] = df_merge["VGV"].round(2)

    df_tabela["Última atividade"] = df_merge["ULTIMA_ATIVIDADE"].dt.strftime(
        "%d/%m/%Y"
    ).fillna("—")

    df_tabela["Dias sem mov."] = df_merge["DIAS_SEM_MOV"].fillna(-1).astype(int)
    df_tabela["Dias sem mov."] = df_tabela["Dias sem mov."].replace(-1, "")

    def alerta_linha(row):
        if row["Status CRM"] != "ATIVO":
            return ""
        leads = row["Leads"]
        analises = row["Análises (só EM)"]
        vendas = row["Vendas"]
        if leads == 0 and analises == 0 and vendas == 0:
            return "Fantasma"
        if leads > 0 and analises == 0:
            return "Leads sem análise"
        if analises > 0 and vendas == 0:
            return "Sem venda"
        return ""

    df_tabela["Alerta"] = df_tabela.apply(alerta_linha, axis=1)

    st.dataframe(
        df_tabela,
        use_container_width=True,
        hide_index=True,
    )

st.markdown("---")

# ---------------------------------------------------------
# ALERTAS INTELIGENTES
# ---------------------------------------------------------
st.markdown(
    """
    <div class="section-title">
        🚨 Alertas Inteligentes
        <span class="badge-chip">Onde focar energia</span>
    </div>
    """,
    unsafe_allow_html=True,
)

if df_merge.empty:
    st.info("Sem dados para gerar alertas com os filtros atuais.")
else:
    ativos_base = df_merge[df_merge["STATUS_CRM"] == "ATIVO"].copy()

    sem_leads = ativos_base[ativos_base["LEADS"] == 0]

    leads_sem_analise = ativos_base[
        (ativos_base["LEADS"] > 0) & (ativos_base["ANALISES_EM"] == 0)
    ]

    analise_sem_venda = ativos_base[
        (ativos_base["ANALISES_EM"] > 0) & (ativos_base["VENDAS"] == 0)
    ]

    limite_dias = 7
    muito_tempo_parado = ativos_base[
        (ativos_base["DIAS_SEM_MOV"].notna())
        & (ativos_base["DIAS_SEM_MOV"] > limite_dias)
    ]

    col_a1, col_a2 = st.columns(2)

    with col_a1:
        st.markdown(
            '<p class="section-subtitle"><span class="alert-text">Ativos sem leads no período</span></p>',
            unsafe_allow_html=True,
        )
        if sem_leads.empty:
            st.caption("Nenhum corretor ativo sem lead no período filtrado.")
        else:
            st.dataframe(
                sem_leads[["NOME_CRM", "EQUIPE", "LEADS", "ANALISES_EM", "VENDAS"]],
                use_container_width=True,
                hide_index=True,
            )

        st.markdown(
            '<p class="section-subtitle"><span class="alert-text">Ativos com leads, mas sem análise</span></p>',
            unsafe_allow_html=True,
        )
        if leads_sem_analise.empty:
            st.caption("Nenhum corretor com leads sem análise.")
        else:
            st.dataframe(
                leads_sem_analise[
                    ["NOME_CRM", "EQUIPE", "LEADS", "ANALISES_EM", "VENDAS"]
                ],
                use_container_width=True,
                hide_index=True,
            )

    with col_a2:
        st.markdown(
            '<p class="section-subtitle"><span class="alert-text">Ativos com análises, mas sem venda</span></p>',
            unsafe_allow_html=True,
        )
        if analise_sem_venda.empty:
            st.caption("Nenhum corretor com análise sem venda no período.")
        else:
            st.dataframe(
                analise_sem_venda[
                    ["NOME_CRM", "EQUIPE", "LEADS", "ANALISES_EM", "VENDAS"]
                ],
                use_container_width=True,
                hide_index=True,
            )

        st.markdown(
            f'<p class="section-subtitle"><span class="alert-text">Ativos há mais de {limite_dias} dias sem movimentação</span></p>',
            unsafe_allow_html=True,
        )
        if muito_tempo_parado.empty:
            st.caption(
                f"Nenhum corretor com mais de {limite_dias} dias sem atividade (lead ou planilha)."
            )
        else:
            st.dataframe(
                muito_tempo_parado[
                    ["NOME_CRM", "EQUIPE", "DIAS_SEM_MOV", "LEADS", "ANALISES_EM", "VENDAS"]
                ],
                use_container_width=True,
                hide_index=True,
            )

st.markdown("---")

# ---------------------------------------------------------
# RANKINGS – MESMA ESTRUTURA ORIGINAL
# ---------------------------------------------------------
st.markdown(
    """
    <div class="section-title">
        🏆 Rankings de Corretores
        <span class="badge-chip">Produção no período</span>
    </div>
    """,
    unsafe_allow_html=True,
)

if df_merge.empty:
    st.info("Sem dados para montar rankings com os filtros atuais.")
else:
    df_rank_base = df_merge.copy()
    df_rank_base["VGV"] = df_rank_base["VGV"].fillna(0.0)

    col_r1, col_r2, col_r3 = st.columns(3)

    # -------------------------- TOP VENDAS --------------------------
    with col_r1:
        st.markdown(
            '<p class="section-subtitle"><span class="good-text">Top por Vendas</span></p>',
            unsafe_allow_html=True,
        )
        top_vendas = df_rank_base.sort_values(
            "VENDAS", ascending=False
        ).head(10)

        if top_vendas.empty:
            st.caption("Sem vendas no período.")
        else:
            st.dataframe(
                top_vendas[["NOME_CRM", "EQUIPE", "VENDAS", "ANALISES_EM"]],
                use_container_width=True,
                hide_index=True,
            )

    # -------------------------- TOP VGV --------------------------
    with col_r2:
        st.markdown(
            '<p class="section-subtitle"><span class="good-text">Top por VGV</span></p>',
            unsafe_allow_html=True,
        )
        top_vgv = df_rank_base.sort_values("VGV", ascending=False).head(10)

        if top_vgv.empty:
            st.caption("Sem VGV registrado no período.")
        else:
            df_show = top_vgv[["NOME_CRM", "EQUIPE", "VGV", "VENDAS"]].copy()
            st.dataframe(
                df_show,
                use_container_width=True,
                hide_index=True,
            )

    # -------------------------- TOP ANÁLISES EM --------------------------
    with col_r3:
        st.markdown(
            '<p class="section-subtitle"><span class="good-text">Top por Análises (só EM)</span></p>',
            unsafe_allow_html=True,
        )
        top_analises = df_rank_base.sort_values(
            "ANALISES_EM", ascending=False
        ).head(10)

        if top_analises.empty:
            st.caption("Sem análises EM ANÁLISE no período.")
        else:
            st.dataframe(
                top_analises[["NOME_CRM", "EQUIPE", "ANALISES_EM", "VENDAS"]],
                use_container_width=True,
                hide_index=True,
            )

st.markdown(
    """
    <p class="small-caption">
        Painel integrado MR Imóveis • Corretores – Visão Geral • CRM + Planilha + Leads
    </p>
    """,
    unsafe_allow_html=True,
)
