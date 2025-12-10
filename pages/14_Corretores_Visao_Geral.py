import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date

# ---------------------------------------------------------
# CONFIG PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Corretores – Visão Geral",
    page_icon="🧑‍💼",
    layout="wide",
)

# Logo lateral
try:
    st.sidebar.image("logo_mr.png", use_column_width=True)
except Exception:
    pass

st.title("🧑‍💼 Corretores – Visão Geral (somente corretores ativos no CRM)")
st.caption(
    "KPIs por corretor (análises, aprovações, vendas), leads recebidos, presença e dias sem ação."
)

# ---------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------
def limpar_data(serie: pd.Series) -> pd.Series:
    dt = pd.to_datetime(serie, errors="coerce", dayfirst=True)
    return dt.dt.date


def format_currency(valor: float) -> str:
    if pd.isna(valor):
        valor = 0
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_cpf(cpf: str) -> str:
    if pd.isna(cpf):
        return "-"
    s = "".join(ch for ch in str(cpf) if ch.isdigit())
    if len(s) == 11:
        return f"{s[0:3]}.{s[3:6]}.{s[6:9]}-{s[9:11]}"
    return s or "-"


# ---------------------------------------------------------
# CARREGAR PLANILHA (MESMO LINK PRINCIPAL)
# ---------------------------------------------------------
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID = "1574157905"
URL_PLANILHA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

try:
    df_planilha_raw = pd.read_csv(URL_PLANILHA, dtype=str)
except Exception:
    st.error("Erro ao carregar a planilha de controle. Verifique o link/conexão.")
    st.stop()

df_planilha = df_planilha_raw.copy()
df_planilha.columns = [c.strip().upper() for c in df_planilha.columns]

map_cols = {
    "DATA BASE": ["DATA BASE", "DATA_BASE", "DT_BASE", "MES_BASE"],
    "DIA": ["DIA", "DATA", "DT_DIA", "DATA DIA"],
    "CORRETOR": ["CORRETOR", "NOME CORRETOR", "NOME_CORRETOR"],
    "STATUS": [
        "STATUS",
        "STATUS ATUAL",
        "STATUS_FINAL",
        "SITUAÇÃO",
        "SITUAÇÃO ATUAL",
        "SITUACAO",
        "SITUACAO ATUAL",
    ],
    "NOME_CLIENTE": ["NOME CLIENTE", "NOME_CLIENTE", "CLIENTE"],
    "CPF_CLIENTE": ["CPF CLIENTE", "CPF_CLIENTE", "CPF"],
    "VALOR_IMOVEL": [
        "VALOR IMOVEL",
        "VALOR_IMOVEL",
        "VALOR DO IMOVEL",
        "VLR_IMOVEL",
        "VGV",
    ],
}


def achar_coluna(possiveis, df_cols):
    for nome in possiveis:
        if nome in df_cols:
            return nome
    return None


col_data_base = achar_coluna(map_cols["DATA BASE"], df_planilha.columns)
col_dia = achar_coluna(map_cols["DIA"], df_planilha.columns)
col_corretor = achar_coluna(map_cols["CORRETOR"], df_planilha.columns)
col_status = achar_coluna(map_cols["STATUS"], df_planilha.columns)
col_nome_cliente = achar_coluna(map_cols["NOME_CLIENTE"], df_planilha.columns)
col_cpf_cliente = achar_coluna(map_cols["CPF_CLIENTE"], df_planilha.columns)
col_valor_imovel = achar_coluna(map_cols["VALOR_IMOVEL"], df_planilha.columns)

if col_data_base is None or col_dia is None or col_corretor is None or col_status is None:
    st.error("Não foi possível identificar colunas essenciais na planilha de controle.")
    st.stop()

df_planilha["DATA_BASE"] = limpar_data(df_planilha[col_data_base])
df_planilha["DIA"] = limpar_data(df_planilha[col_dia])
df_planilha["CORRETOR"] = (
    df_planilha[col_corretor]
    .fillna("SEM CORRETOR")
    .astype(str)
    .str.upper()
    .str.strip()
)
df_planilha["STATUS_BRUTO"] = df_planilha[col_status].fillna("").astype(str).str.upper()

if col_nome_cliente:
    df_planilha["NOME_CLIENTE_BASE"] = df_planilha[col_nome_cliente].fillna("").astype(
        str
    )
else:
    df_planilha["NOME_CLIENTE_BASE"] = ""

if col_cpf_cliente:
    df_planilha["CPF_CLIENTE_BASE"] = df_planilha[col_cpf_cliente].fillna("").astype(
        str
    )
else:
    df_planilha["CPF_CLIENTE_BASE"] = ""

if col_valor_imovel:
    df_planilha["VALOR_IMOVEL_BASE"] = (
        df_planilha[col_valor_imovel]
        .astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    df_planilha["VALOR_IMOVEL_BASE"] = pd.to_numeric(
        df_planilha["VALOR_IMOVEL_BASE"], errors="coerce"
    ).fillna(0.0)
else:
    df_planilha["VALOR_IMOVEL_BASE"] = 0.0

s = df_planilha["STATUS_BRUTO"]
df_planilha["STATUS_BASE"] = ""

df_planilha.loc[
    s.str.contains("ANÁLISE") | s.str.contains("ANALISE"), "STATUS_BASE"
] = "ANÁLISE"
df_planilha.loc[s.str.contains("APROV"), "STATUS_BASE"] = "APROVADO"
df_planilha.loc[s.str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
df_planilha.loc[
    s.str.contains("REANÁLISE") | s.str.contains("REANALISE"), "STATUS_BASE"
] = "REANÁLISE"
df_planilha.loc[s.str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA GERADA"
df_planilha.loc[s.str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA INFORMADA"
df_planilha.loc[s.str.contains("DESIST", na=False), "STATUS_BASE"] = "DESISTIU"
df_planilha["STATUS_BASE"] = df_planilha["STATUS_BASE"].replace("", "OUTROS")

# STATUS FINAL POR CLIENTE
df_status_final = df_planilha.dropna(subset=["NOME_CLIENTE_BASE"]).copy()
df_status_final["CHAVE_CLIENTE"] = (
    df_status_final["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO")
    + " | "
    + df_status_final["CPF_CLIENTE_BASE"].fillna("")
)
df_status_final = df_status_final.sort_values("DIA")
status_final_por_cliente = df_status_final.groupby("CHAVE_CLIENTE", as_index=False)[
    ["DIA", "STATUS_BASE"]
].last()
status_final_por_cliente = status_final_por_cliente.rename(
    columns={"STATUS_BASE": "STATUS_FINAL_CLIENTE"}
)

# ---------------------------------------------------------
# BASE CRM – df_leads DO SESSION_STATE
# ---------------------------------------------------------
# Tenta buscar o df_leads carregado na página principal.
df_leads_raw = st.session_state.get("df_leads", None)

if df_leads_raw is None or getattr(df_leads_raw, "empty", True):
    # Se não tiver nada no session_state, segue com DataFrame vazio
    df_leads = pd.DataFrame()
else:
    df_leads = df_leads_raw.copy()

lower_cols = {c.lower(): c for c in df_leads.columns}


def get_col(possiveis):
    for nome in possiveis:
        if nome in lower_cols:
            return lower_cols[nome]
    return None


if df_leads.empty:
    # Garante colunas esperadas mesmo sem dados
    df_leads["CORRETOR_CRM"] = []
    df_leads["DATA_CAPTURA_DT"] = pd.to_datetime([])
    df_leads["DATA_COM_CORRETOR_DT"] = pd.to_datetime([])
    df_leads["DATA_ULT_INTERACAO_DT"] = pd.to_datetime([])
    df_leads["ULT_ATIVIDADE_CRM"] = pd.to_datetime([])
else:
    # Corretor no CRM
    col_corretor_crm = get_col(
        [
            "nome_corretor_norm",
            "nome_corretor",
            "corretor",
            "responsavel",
            "responsável",
            "usuario_responsavel",
            "usuario",
        ]
    )

    if not col_corretor_crm:
        st.error("Não foi possível identificar a coluna de corretor nos dados do CRM.")
        st.stop()

    df_leads["CORRETOR_CRM"] = (
        df_leads[col_corretor_crm]
        .fillna("SEM CORRETOR")
        .astype(str)
        .str.upper()
        .str.strip()
    )

    # Datas
    col_data_captura = get_col(["data_captura", "data do lead", "data_lead"])
    if col_data_captura:
        df_leads["DATA_CAPTURA_DT"] = pd.to_datetime(
            df_leads[col_data_captura], errors="coerce"
        )
    else:
        df_leads["DATA_CAPTURA_DT"] = pd.NaT

    col_data_com_corretor = get_col(
        ["data_com_corretor", "data_primeiro_atendimento"]
    )
    if col_data_com_corretor:
        df_leads["DATA_COM_CORRETOR_DT"] = pd.to_datetime(
            df_leads[col_data_com_corretor], errors="coerce"
        )
    else:
        df_leads["DATA_COM_CORRETOR_DT"] = pd.NaT

    col_data_ult_inter = get_col(
        [
            "data_ultima_interacao",
            "data_última_interacao",
            "data_ultima_atividade",
        ]
    )
    if col_data_ult_inter:
        df_leads["DATA_ULT_INTERACAO_DT"] = pd.to_datetime(
            df_leads[col_data_ult_inter], errors="coerce"
        )
    else:
        df_leads["DATA_ULT_INTERACAO_DT"] = pd.NaT

    # Última atividade no CRM
    df_leads["ULT_ATIVIDADE_CRM"] = df_leads[
        ["DATA_CAPTURA_DT", "DATA_COM_CORRETOR_DT", "DATA_ULT_INTERACAO_DT"]
    ].max(axis=1)
    df_leads["ULT_ATIVIDADE_CRM"] = pd.to_datetime(
        df_leads["ULT_ATIVIDADE_CRM"], errors="coerce"
    )

# ---------------------------------------------------------
# FILTROS (PERÍODO E TIPO DE VENDA)
# ---------------------------------------------------------
st.sidebar.title("Filtros – Corretores")

dias_validos = df_planilha["DIA"].dropna()

# Se não houver nenhuma data válida, usa hoje como fallback
if dias_validos.empty:
    data_min = date.today() - timedelta(days=30)
    data_max = date.today()
else:
    data_min = dias_validos.min()
    data_max = dias_validos.max()

default_ini = max(data_min, data_max - timedelta(days=30))

periodo = st.sidebar.date_input(
    "Período (base: DIA da planilha)",
    value=(default_ini, data_max),
    min_value=data_min,
    max_value=data_max,
)

if isinstance(periodo, (tuple, list)) and len(periodo) == 2:
    data_ini, data_fim = periodo
else:
    data_ini = periodo
    data_fim = periodo

tipo_venda = st.sidebar.radio(
    "Tipo de vendas para KPIs",
    options=[
        "GERADAS + INFORMADAS",
        "Apenas GERADAS",
        "Apenas INFORMADAS",
    ],
    index=0,
)

st.caption(
    f"Período selecionado: **{data_ini.strftime('%d/%m/%Y')}** até **{data_fim.strftime('%d/%m/%Y')}**"
)

# Corretores ativos no CRM (base inicial)
corretores_ativos_crm = (
    df_leads["CORRETOR_CRM"]
    .dropna()
    .astype(str)
    .str.upper()
    .replace("", "SEM CORRETOR")
    .unique()
)
corretores_ativos = sorted(
    [c for c in corretores_ativos_crm if c not in ["SEM CORRETOR"]]
)

# Se por algum motivo não houver nenhum corretor no CRM, mostra aviso
if not corretores_ativos:
    st.warning("Nenhum corretor encontrado nos dados do CRM para o período.")
    st.stop()

# ---------------------------------------------------------
# KPIs POR CORRETOR (PLANILHA)
# ---------------------------------------------------------
mask_periodo = (df_planilha["DIA"] >= data_ini) & (df_planilha["DIA"] <= data_fim)
df_periodo = df_planilha[mask_periodo].copy()

# Garante apenas corretores ativos
df_periodo = df_periodo[df_periodo["CORRETOR"].isin(corretores_ativos)]

# Análises (EM ANÁLISE + REANÁLISE)
mask_analise = df_periodo["STATUS_BASE"].isin(["ANÁLISE", "EM ANÁLISE", "REANÁLISE"])
df_analises = df_periodo[mask_analise].groupby("CORRETOR", as_index=False).size()
df_analises = df_analises.rename(columns={"size": "ANALISES"})

df_aprov = df_periodo[df_periodo["STATUS_BASE"] == "APROVADO"].groupby(
    "CORRETOR", as_index=False
).size()
df_aprov = df_aprov.rename(columns={"size": "APROVACOES"})

df_reprov = df_periodo[df_periodo["STATUS_BASE"] == "REPROVADO"].groupby(
    "CORRETOR", as_index=False
).size()
df_reprov = df_reprov.rename(columns={"size": "REPROVACOES"})

# VENDAS (respeitando regra do STATUS FINAL != DESISTIU)
df_vendas_ref = df_periodo.copy()
df_vendas_ref["CHAVE_CLIENTE"] = (
    df_vendas_ref["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO")
    + " | "
    + df_vendas_ref["CPF_CLIENTE_BASE"].fillna("")
)

if not status_final_por_cliente.empty:
    df_vendas_ref = df_vendas_ref.merge(
        status_final_por_cliente,
        on="CHAVE_CLIENTE",
        how="left",
    )
    df_vendas_ref = df_vendas_ref[df_vendas_ref["STATUS_FINAL_CLIENTE"] != "DESISTIU"]

# 👉 Blinda para só ordenar se tiver coluna DIA e tiver linhas
if (not df_vendas_ref.empty) and ("DIA" in df_vendas_ref.columns):
    df_vendas_ref = df_vendas_ref.sort_values("DIA")
    df_vendas_ref["CHAVE_CLIENTE"] = (
        df_vendas_ref["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO")
        + " | "
        + df_vendas_ref["CPF_CLIENTE_BASE"].fillna("")
    )

    df_vendas_ult = df_vendas_ref.groupby("CHAVE_CLIENTE", as_index=False).tail(1)

    if tipo_venda == "GERADAS + INFORMADAS":
        mask_venda = df_vendas_ult["STATUS_BASE"].isin(
            ["VENDA GERADA", "VENDA INFORMADA"]
        )
    elif tipo_venda == "Apenas GERADAS":
        mask_venda = df_vendas_ult["STATUS_BASE"].eq("VENDA GERADA")
    else:
        mask_venda = df_vendas_ult["STATUS_BASE"].eq("VENDA INFORMADA")

    df_vendas_final = df_vendas_ult[mask_venda].copy()
else:
    # Se não tiver dados ou não tiver coluna DIA, segue com DF vazio
    df_vendas_final = df_vendas_ref.iloc[0:0].copy()

# Agrupa vendas por corretor (quantidade e VGV)
if df_vendas_final.empty:
    df_vendas_cor = pd.DataFrame(columns=["CORRETOR", "VENDAS", "VGV"])
else:
    df_vendas_cor = df_vendas_final.groupby("CORRETOR", as_index=False).agg(
        VENDAS=("VALOR_IMOVEL_BASE", "size"),
        VGV=("VALOR_IMOVEL_BASE", "sum"),
    )

# Monta base de KPIs da planilha
df_kpis_plan = (
    df_periodo[["CORRETOR"]]
    .drop_duplicates()
    .merge(df_analises, on="CORRETOR", how="left")
    .merge(df_aprov, on="CORRETOR", how="left")
    .merge(df_reprov, on="CORRETOR", how="left")
    .merge(df_vendas_cor, on="CORRETOR", how="left")
)

for col in ["ANALISES", "APROVACOES", "REPROVACOES", "VENDAS"]:
    df_kpis_plan[col] = df_kpis_plan[col].fillna(0).astype(int)

df_kpis_plan["VGV"] = df_kpis_plan["VGV"].fillna(0.0)
df_kpis_plan["TICKET_MEDIO"] = np.where(
    df_kpis_plan["VENDAS"] > 0,
    df_kpis_plan["VGV"] / df_kpis_plan["VENDAS"],
    0,
)

df_kpis_plan["TAXA_APROV_ANALISE"] = np.where(
    df_kpis_plan["ANALISES"] > 0,
    df_kpis_plan["APROVACOES"] / df_kpis_plan["ANALISES"] * 100,
    0,
)

df_kpis_plan["TAXA_VENDA_ANALISE"] = np.where(
    df_kpis_plan["ANALISES"] > 0,
    df_kpis_plan["VENDAS"] / df_kpis_plan["ANALISES"] * 100,
    0,
)

df_kpis_plan["TAXA_VENDA_APROV"] = np.where(
    df_kpis_plan["APROVACOES"] > 0,
    df_kpis_plan["VENDAS"] / df_kpis_plan["APROVACOES"] * 100,
    0,
)

# ---------------------------------------------------------
# LEADS POR CORRETOR (CRM)
# ---------------------------------------------------------
if df_leads.empty:
    df_leads_periodo = df_leads.copy()
    df_leads_count = pd.DataFrame(columns=["CORRETOR", "LEADS"])
else:
    mask_crm_periodo = (df_leads["DATA_CAPTURA_DT"].dt.date >= data_ini) & (
        df_leads["DATA_CAPTURA_DT"].dt.date <= data_fim
    )
    df_leads_periodo = df_leads[mask_crm_periodo].copy()

    df_leads_count = (
        df_leads_periodo.groupby("CORRETOR_CRM", as_index=False)
        .size()
        .rename(columns={"CORRETOR_CRM": "CORRETOR", "size": "LEADS"})
    )

# ---------------------------------------------------------
# ÚLTIMO MOVIMENTO (PLANILHA + CRM)
# ---------------------------------------------------------
df_ult_plan = (
    df_planilha.dropna(subset=["DIA"])
    .sort_values("DIA")
    .groupby("CORRETOR", as_index=False)["DIA"]
    .last()
    .rename(columns={"DIA": "ULTIMO_PLANILHA"})
)

if df_leads.empty:
    df_ult_crm = pd.DataFrame(columns=["CORRETOR", "ULTIMO_CRM"])
else:
    df_ult_crm = (
        df_leads.dropna(subset=["ULT_ATIVIDADE_CRM"])
        .sort_values("ULT_ATIVIDADE_CRM")
        .groupby("CORRETOR_CRM", as_index=False)["ULT_ATIVIDADE_CRM"]
        .last()
        .rename(columns={"CORRETOR_CRM": "CORRETOR", "ULT_ATIVIDADE_CRM": "ULTIMO_CRM"})
    )

df_ult_mov = df_ult_plan.merge(df_ult_crm, on="CORRETOR", how="outer")
df_ult_mov["ULTIMO_PLANILHA"] = pd.to_datetime(
    df_ult_mov["ULTIMO_PLANILHA"], errors="coerce"
)
df_ult_mov["ULTIMO_CRM"] = pd.to_datetime(df_ult_mov["ULTIMO_CRM"], errors="coerce")

df_ult_mov["ULTIMO_MOVIMENTO"] = df_ult_mov[
    ["ULTIMO_PLANILHA", "ULTIMO_CRM"]
].max(axis=1)

hoje = date.today()
df_ult_mov["DIAS_SEM_MOV"] = (
    hoje - df_ult_mov["ULTIMO_MOVIMENTO"].dt.date
).dt.days

# ---------------------------------------------------------
# PRESENÇA / DIAS COM AÇÃO
# ---------------------------------------------------------
corretores_ativos = sorted(df_kpis_plan["CORRETOR"].unique().tolist())

df_plan_pres = df_planilha[
    df_planilha["CORRETOR"].isin(corretores_ativos)
].dropna(subset=["DIA"])[["CORRETOR", "DIA"]].copy()
df_plan_pres["PRESENTE"] = True

df_leads_val = df_leads[df_leads["CORRETOR_CRM"].isin(corretores_ativos)].copy()
col_dias_atividade = [
    "DATA_CAPTURA_DT",
    "DATA_COM_CORRETOR_DT",
    "DATA_ULT_INTERACAO_DT",
]
dfs_crm_pres = []
for col in col_dias_atividade:
    tmp = df_leads_val[
        (df_leads_val[col].notna())
        & (df_leads_val[col].dt.date >= data_ini)
        & (df_leads_val[col].dt.date <= data_fim)
    ][["CORRETOR_CRM", col]].copy()
    if not tmp.empty:
        tmp["DIA"] = tmp[col].dt.date
        tmp = tmp.rename(columns={"CORRETOR_CRM": "CORRETOR"})
        dfs_crm_pres.append(tmp[["CORRETOR", "DIA"]])

if dfs_crm_pres:
    df_pres_crm = pd.concat(dfs_crm_pres, ignore_index=True).drop_duplicates()
    df_pres_crm["PRESENTE"] = True
else:
    df_pres_crm = pd.DataFrame(columns=["CORRETOR", "DIA", "PRESENTE"])

df_pres_total = pd.concat(
    [df_plan_pres, df_pres_crm],
    ignore_index=True,
).drop_duplicates(subset=["CORRETOR", "DIA"])

dias_range = pd.date_range(data_ini, data_fim, freq="D").date
idx = pd.MultiIndex.from_product(
    [corretores_ativos, dias_range], names=["CORRETOR", "DIA"]
)
df_grid = pd.DataFrame(index=idx).reset_index()

df_grid = df_grid.merge(
    df_pres_total[["CORRETOR", "DIA", "PRESENTE"]],
    on=["CORRETOR", "DIA"],
    how="left",
)
df_grid["PRESENTE"] = df_grid["PRESENTE"].fillna(False)

df_faltas = df_grid.groupby("CORRETOR", as_index=False).agg(
    TOTAL_DIAS=("DIA", "nunique"),
    DIAS_PRESENTE=("PRESENTE", "sum"),
)
df_faltas["FALTAS"] = df_faltas["TOTAL_DIAS"] - df_faltas["DIAS_PRESENTE"]

df_faltas["PRESENCA_PCT"] = np.where(
    df_faltas["TOTAL_DIAS"] > 0,
    df_faltas["DIAS_PRESENTE"] / df_faltas["TOTAL_DIAS"] * 100,
    0,
)

# ---------------------------------------------------------
# TABELA FINAL POR CORRETOR
# ---------------------------------------------------------
df_base = pd.DataFrame({"CORRETOR": corretores_ativos})

df_base = (
    df_base.merge(df_kpis_plan, on="CORRETOR", how="left")
    .merge(df_leads_count, on="CORRETOR", how="left")
    .merge(
        df_ult_mov[["CORRETOR", "ULTIMO_MOVIMENTO", "DIAS_SEM_MOV"]],
        on="CORRETOR",
        how="left",
    )
    .merge(
        df_faltas[
            ["CORRETOR", "FALTAS", "TOTAL_DIAS", "DIAS_PRESENTE", "PRESENCA_PCT"]
        ],
        on="CORRETOR",
        how="left",
    )
)

for col in [
    "LEADS",
    "ANALISES",
    "APROVACOES",
    "REPROVACOES",
    "VENDAS",
    "TOTAL_DIAS",
    "DIAS_PRESENTE",
    "FALTAS",
]:
    df_base[col] = df_base[col].fillna(0).astype(int)

df_base["VGV"] = df_base["VGV"].fillna(0.0)
df_base["TICKET_MEDIO"] = df_base["TICKET_MEDIO"].fillna(0.0)
df_base["PRESENCA_PCT"] = df_base["PRESENCA_PCT"].fillna(0.0)

# Remove quem está há mais de 30 dias sem movimento total
df_base = df_base[
    (df_base["DIAS_SEM_MOV"].isna()) | (df_base["DIAS_SEM_MOV"] <= 30)
].reset_index(drop=True)

# ---------------------------------------------------------
# EXIBIÇÃO
# ---------------------------------------------------------
df_exibe = df_base.copy()
df_exibe = df_exibe.rename(columns={"FALTAS": "Dias sem ação"})

df_exibe["VGV"] = df_exibe["VGV"].apply(format_currency)
df_exibe["Ticket médio"] = df_exibe["TICKET_MEDIO"].apply(format_currency)
df_exibe["Taxa aprov./análises (%)"] = df_exibe["TAXA_APROV_ANALISE"].apply(
    lambda x: f"{x:.1f}%"
)
df_exibe["Taxa vendas/análises (%)"] = df_exibe["TAXA_VENDA_ANALISE"].apply(
    lambda x: f"{x:.1f}%"
)
df_exibe["Taxa vendas/aprovações (%)"] = df_exibe["TAXA_VENDA_APROV"].apply(
    lambda x: f"{x:.1f}%"
)
df_exibe["Presença (%)"] = df_exibe["PRESENCA_PCT"].apply(
    lambda x: f"{x:.1f}%"
)

df_exibe["Último movimento"] = df_exibe["ULTIMO_MOVIMENTO"].apply(
    lambda d: d.strftime("%d/%m/%Y") if pd.notna(d) else "-"
)
df_exibe["Dias sem movimento"] = df_exibe["DIAS_SEM_MOV"].apply(
    lambda x: int(x) if pd.notna(x) else "-"
)

colunas_ordem = [
    "CORRETOR",
    "LEADS",
    "ANALISES",
    "APROVACOES",
    "REPROVACOES",
    "VENDAS",
    "VGV",
    "Ticket médio",
    "Taxa aprov./análises (%)",
    "Taxa vendas/análises (%)",
    "Taxa vendas/aprovações (%)",
    "Dias sem ação",
    "TOTAL_DIAS",
    "Presença (%)",
    "Último movimento",
    "Dias sem movimento",
]
colunas_ordem = [c for c in colunas_ordem if c in df_exibe.columns]
df_exibe = df_exibe[colunas_ordem].sort_values("CORRETOR")

st.markdown("### 📊 Tabela consolidada por corretor (somente ativos no CRM)")
st.dataframe(df_exibe, use_container_width=True, hide_index=True)

st.markdown("---")
st.markdown("### 🔍 Visão individual")

corretor_sel = st.selectbox(
    "Selecione um corretor",
    options=["Todos"] + sorted(df_base["CORRETOR"].unique().tolist()),
)

if corretor_sel != "Todos" and corretor_sel in df_base["CORRETOR"].values:
    linha = df_base[df_base["CORRETOR"] == corretor_sel].iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Leads", int(linha.get("LEADS", 0)))
    c2.metric("Análises", int(linha.get("ANALISES", 0)))
    c3.metric("Aprovações", int(linha.get("APROVACOES", 0)))
    c4.metric("Vendas", int(linha.get("VENDAS", 0)))

    c5, c6, c7 = st.columns(3)
    c5.metric("VGV", format_currency(linha.get("VGV", 0)))
    c6.metric("Ticket médio", format_currency(linha.get("TICKET_MEDIO", 0)))
    c7.metric(
        "Taxa aprov./análises",
        f"{linha.get('TAXA_APROV_ANALISE', 0):.1f}%",
    )

    c8, c9, c10 = st.columns(3)
    c8.metric(
        "Taxa vendas/análises",
        f"{linha.get('TAXA_VENDA_ANALISE', 0):.1f}%",
    )
    c9.metric(
        "Taxa vendas/aprovações",
        f"{linha.get('TAXA_VENDA_APROV', 0):.1f}%",
    )
    c10.metric(
        "Presença",
        f"{linha.get('PRESENCA_PCT', 0):.1f}%",
    )

    c11, c12, c13 = st.columns(3)
    ult_mov = linha.get("ULTIMO_MOVIMENTO", None)
    dias_sem = linha.get("DIAS_SEM_MOV", None)
    c11.metric(
        "Último movimento",
        ult_mov.strftime("%d/%m/%Y") if pd.notna(ult_mov) else "-",
    )
    c12.metric(
        "Dias sem movimento",
        int(dias_sem) if pd.notna(dias_sem) else "-",
    )
    c13.metric(
        "Dias sem ação",
        int(linha.get("FALTAS", 0)),
    )

    st.info(
        "Movimento considera qualquer atividade na planilha (análises, vendas, etc.) "
        "e qualquer atividade no CRM (captura, primeiro contato ou última interação). "
        "Se em um dia não houve nenhuma dessas ações, o dia conta como **dia sem ação**."
    )
