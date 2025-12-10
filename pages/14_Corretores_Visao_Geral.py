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

# ---------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------
@st.cache_data
def carregar_planilha_controle() -> pd.DataFrame:
    """
    Carrega a planilha de controle de processos (mesma base do app principal).
    """
    SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
    GID = "1574157905"
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

    df = pd.read_csv(url, dtype=str)
    return df


def limpar_data(serie: pd.Series) -> pd.Series:
    dt = pd.to_datetime(serie, errors="coerce", dayfirst=True)
    return dt.dt.date


def format_currency(valor: float) -> str:
    if pd.isna(valor):
        valor = 0
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_cpf(cpf: str) -> str:
    """Formata CPF no padrão 000.000.000-00, se possível."""
    if pd.isna(cpf):
        return "-"
    s = "".join(ch for ch in str(cpf) if ch.isdigit())
    if len(s) == 11:
        return f"{s[0:3]}.{s[3:6]}.{s[6:9]}-{s[9:11]}"
    return s or "-"


# ---------------------------------------------------------
# BASE PLANILHA (MESMA LÓGICA DO APP PRINCIPAL)
# ---------------------------------------------------------
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID = "1574157905"
URL_PLANILHA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

try:
    df_planilha_raw = pd.read_csv(URL_PLANILHA, dtype=str)
except Exception as e:
    st.error(
        "Erro ao carregar a planilha de controle de processos. "
        "Verifique a conexão ou o link da planilha."
    )
    st.stop()

df_planilha = df_planilha_raw.copy()
df_planilha.columns = [c.strip().upper() for c in df_planilha.columns]

map_cols = {
    "DATA BASE": ["DATA BASE", "DATA_BASE", "DT_BASE", "MES_BASE"],
    "DIA": ["DIA", "DATA", "DT_DIA", "DATA DIA"],
    "CORRETOR": ["CORRETOR", "NOME CORRETOR", "NOME_CORRETOR"],
    # 👇 AQUI ESTAVA O PROBLEMA – AGORA ACEITA SITUAÇÃO TAMBÉM
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
# Tenta pegar do session_state. Se não tiver, segue com DF vazio.
df_leads_raw = st.session_state.get("df_leads", pd.DataFrame())

if df_leads_raw is None or getattr(df_leads_raw, "empty", True):
    df_leads = pd.DataFrame()
else:
    df_leads = df_leads_raw.copy()
lower_cols = {c.lower(): c for c in df_leads.columns}


def get_col(possiveis):
    for nome in possiveis:
        if nome in lower_cols:
            return lower_cols[nome]
    return None


col_corretor_crm = get_col(["corretor", "nome_corretor", "usuario"])
if not col_corretor_crm:
    st.error("Não foi possível identificar a coluna de corretor nos dados do CRM.")
    st.stop()

df_leads["CORRETOR_CRM"] = (
    df_leads[col_corretor_crm].fillna("SEM CORRETOR").astype(str).str.upper().str.strip()
)

col_data_captura = get_col(["data_captura", "data do lead", "data_lead"])
if col_data_captura:
    df_leads["DATA_CAPTURA_DT"] = pd.to_datetime(
        df_leads[col_data_captura], errors="coerce"
    )
else:
    df_leads["DATA_CAPTURA_DT"] = pd.NaT

col_data_com_corretor = get_col(["data_com_corretor", "data_primeiro_atendimento"])
if col_data_com_corretor:
    df_leads["DATA_COM_CORRETOR_DT"] = pd.to_datetime(
        df_leads[col_data_com_corretor], errors="coerce"
    )
else:
    df_leads["DATA_COM_CORRETOR_DT"] = pd.NaT

col_data_ult_inter = get_col(
    ["data_ultima_interacao", "data_última_interacao", "data_ultima_atividade"]
)
if col_data_ult_inter:
    df_leads["DATA_ULT_INTERACAO_DT"] = pd.to_datetime(
        df_leads[col_data_ult_inter], errors="coerce"
    )
else:
    df_leads["DATA_ULT_INTERACAO_DT"] = pd.NaT

df_leads["ULT_ATIVIDADE_CRM"] = df_leads[
    ["DATA_CAPTURA_DT", "DATA_COM_CORRETOR_DT", "DATA_ULT_INTERACAO_DT"]
].max(axis=1)
df_leads["ULT_ATIVIDADE_CRM"] = pd.to_datetime(
    df_leads["ULT_ATIVIDADE_CRM"], errors="coerce"
)

# ---------------------------------------------------------
# SIDEBAR - PARAMETROS GERAIS
# ---------------------------------------------------------
st.sidebar.header("⚙️ Filtros gerais")

tipo_venda = st.sidebar.radio(
    "Qual tipo de venda considerar?",
    ["GERADAS + INFORMADAS", "Apenas GERADAS", "Apenas INFORMADAS"],
    index=0,
    help=(
        "• GERADAS + INFORMADAS: considera qualquer venda gerada ou informada.\n"
        "• Apenas GERADAS: só conta vendas com status 'VENDA GERADA'.\n"
        "• Apenas INFORMADAS: só conta vendas com status 'VENDA INFORMADA'."
    ),
)

min_data_base = df_planilha["DATA_BASE"].min()
max_data_base = df_planilha["DATA_BASE"].max()

data_base_ini, data_base_fim = st.sidebar.date_input(
    "Período de DATA BASE (planilha)",
    value=(min_data_base, max_data_base),
    min_value=min_data_base,
    max_value=max_data_base,
)

if isinstance(data_base_ini, tuple) or isinstance(data_base_ini, list):
    data_base_ini, data_base_fim = data_base_ini

if data_base_ini > data_base_fim:
    st.sidebar.error("A data inicial não pode ser maior que a data final.")
    st.stop()

st.sidebar.markdown("---")

dias_retroativos = st.sidebar.slider(
    "Período (dias) para análise de movimento/presença",
    min_value=7,
    max_value=90,
    value=30,
)
data_fim = date.today()
data_ini = data_fim - timedelta(days=dias_retroativos - 1)

st.sidebar.caption(
    f"Presença e últimas atividades avaliadas de {data_ini.strftime('%d/%m/%Y')} "
    f"até {data_fim.strftime('%d/%m/%Y')}."
)

# ---------------------------------------------------------
# FILTRO DE PLANILHA POR DATA BASE
# ---------------------------------------------------------
mask_base = (df_planilha["DATA_BASE"] >= data_base_ini) & (
    df_planilha["DATA_BASE"] <= data_base_fim
)
df_plan_base = df_planilha[mask_base].copy()

# ---------------------------------------------------------
# 1) KPIs POR CORRETOR (PLANILHA)
# ---------------------------------------------------------
df_kpis_plan = df_plan_base.copy()

mask_analise = df_kpis_plan["STATUS_BASE"].isin(["ANÁLISE", "EM ANÁLISE", "REANÁLISE"])
df_analises = df_kpis_plan[mask_analise].groupby("CORRETOR", as_index=False).size()
df_analises = df_analises.rename(columns={"size": "ANALISES"})

df_aprov = df_kpis_plan[df_kpis_plan["STATUS_BASE"] == "APROVADO"].groupby(
    "CORRETOR", as_index=False
).size()
df_aprov = df_aprov.rename(columns={"size": "APROVACOES"})

df_reprov = df_kpis_plan[df_kpis_plan["STATUS_BASE"] == "REPROVADO"].groupby(
    "CORRETOR", as_index=False
).size()
df_reprov = df_reprov.rename(columns={"size": "REPROVACOES"})

df_vendas_ref = df_plan_base.copy()
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

if not df_vendas_ref.empty:
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
    df_vendas_final = df_vendas_ref.iloc[0:0].copy()

df_vendas_cor = (
    df_vendas_final.groupby("CORRETOR", as_index=False)["VALOR_IMOVEL_BASE"]
    .agg(VENDAS=("VALOR_IMOVEL_BASE", "size"), VGV=("VALOR_IMOVEL_BASE", "sum"))
)

df_kpis_plan = (
    df_kpis_plan[["CORRETOR"]]
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
# 2) LEADS POR CORRETOR (CRM)
# ---------------------------------------------------------
mask_crm_periodo = (df_leads["DATA_CAPTURA_DT"].dt.date >= data_ini) & (
    df_leads["DATA_CAPTURA_DT"].dt.date <= data_fim
)
df_leads_periodo = df_leads[mask_crm_periodo].copy()

df_leads_count = (
    df_leads_periodo.groupby("CORRETOR_CRM", as_index=False).size().rename(
        columns={"CORRETOR_CRM": "CORRETOR", "size": "LEADS"}
    )
)

# ---------------------------------------------------------
# 3) ÚLTIMO MOVIMENTO (PLANILHA + CRM)
# ---------------------------------------------------------
df_ult_plan = (
    df_planilha.dropna(subset=["DIA"])
    .sort_values("DIA")
    .groupby("CORRETOR", as_index=False)["DIA"]
    .last()
    .rename(columns={"DIA": "ULTIMO_PLANILHA"})
)

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
df_ult_mov["DIAS_SEM_MOV"] = (hoje - df_ult_mov["ULTIMO_MOVIMENTO"].dt.date).dt.days

# ---------------------------------------------------------
# 4) PRESENÇA / DIAS COM AÇÃO (PLANILHA + CRM)
# ---------------------------------------------------------
corretores_ativos = sorted(
    set(df_kpis_plan["CORRETOR"].unique().tolist())
    | set(df_leads["CORRETOR_CRM"].unique().tolist())
)

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
# 4.1) BASE CORRETORES – DADOS PESSOAIS (API)
# ---------------------------------------------------------
df_cor_api_raw = st.session_state.get("df_corretores_api", pd.DataFrame())

if df_cor_api_raw is not None and not df_cor_api_raw.empty:
    df_cor_api = df_cor_api_raw.copy()
    df_cor_api.columns = [c.lower().strip() for c in df_cor_api.columns]

    def _get_col_cor(possiveis):
        for nome in possiveis:
            if nome in df_cor_api.columns:
                return nome
        return None

    col_nome_cor = _get_col_cor(["nome", "nome_corretor"])
    if col_nome_cor:
        df_cor_api["CORRETOR"] = (
            df_cor_api[col_nome_cor]
            .fillna("NÃO INFORMADO")
            .astype(str)
            .str.upper()
            .str.strip()
        )
    else:
        df_cor_api["CORRETOR"] = ""

    col_cpf_cor = _get_col_cor(["cpf_cnpj", "cpf", "documento"])
    if col_cpf_cor:
        df_cor_api["CPF_CORRETOR"] = (
            df_cor_api[col_cpf_cor]
            .fillna("")
            .astype(str)
            .str.replace(r"\D", "", regex=True)
        )
    else:
        df_cor_api["CPF_CORRETOR"] = ""

    col_email_cor = _get_col_cor(["email"])
    if col_email_cor:
        df_cor_api["EMAIL_CORRETOR"] = (
            df_cor_api[col_email_cor].fillna("").astype(str).str.strip()
        )
    else:
        df_cor_api["EMAIL_CORRETOR"] = ""

    col_ddd = _get_col_cor(["ddd", "ddi", "ddd_telefone"])
    col_tel = _get_col_cor(["telefone", "telefone_celular", "celular"])
    if col_tel:
        ddd_series = (
            df_cor_api[col_ddd].fillna("").astype(str).str.strip()
            if col_ddd
            else ""
        )
        tel_series = df_cor_api[col_tel].fillna("").astype(str).str.strip()
        df_cor_api["TELEFONE_CORRETOR"] = (
            ddd_series.where(ddd_series == "", ddd_series + " ") + tel_series
        ).str.strip()
    else:
        df_cor_api["TELEFONE_CORRETOR"] = ""

    col_creci_cor = _get_col_cor(["creci"])
    if col_creci_cor:
        df_cor_api["CRECI_CORRETOR"] = (
            df_cor_api[col_creci_cor].fillna("").astype(str).str.strip()
        )
    else:
        df_cor_api["CRECI_CORRETOR"] = ""

    col_aniv_cor = _get_col_cor(["aniversario", "data_nascimento", "nascimento"])
    if col_aniv_cor:
        df_cor_api["ANIVERSARIO_CORRETOR"] = pd.to_datetime(
            df_cor_api[col_aniv_cor], errors="coerce"
        ).dt.date
    else:
        df_cor_api["ANIVERSARIO_CORRETOR"] = pd.NaT

    col_status_cor = _get_col_cor(["status"])
    if col_status_cor:
        def _map_status(v):
            try:
                vi = int(v)
                return "ATIVO" if vi == 1 else "INATIVO"
            except Exception:
                return str(v).upper() if pd.notna(v) else ""

        df_cor_api["STATUS_CORRETOR"] = df_cor_api[col_status_cor].apply(_map_status)
    else:
        df_cor_api["STATUS_CORRETOR"] = ""

    for flag, novo in [
        ("fl_notificacoes_email", "NOTIF_EMAIL"),
        ("fl_notificacoes_whatsapp", "NOTIF_WHATSAPP"),
        ("fl_notificacoes_push", "NOTIF_PUSH"),
    ]:
        col_flag = _get_col_cor([flag])
        if col_flag:
            df_cor_api[novo] = df_cor_api[col_flag].apply(
                lambda x: "Sim" if str(x) in ["1", "True", "true"] else "Não"
            )
        else:
            df_cor_api[novo] = ""

    cols_keep = [
        "CORRETOR",
        "CPF_CORRETOR",
        "EMAIL_CORRETOR",
        "TELEFONE_CORRETOR",
        "CRECI_CORRETOR",
        "ANIVERSARIO_CORRETOR",
        "STATUS_CORRETOR",
        "NOTIF_EMAIL",
        "NOTIF_WHATSAPP",
        "NOTIF_PUSH",
    ]
    df_cor_api = df_cor_api[
        [c for c in cols_keep if c in df_cor_api.columns]
    ].drop_duplicates(subset=["CORRETOR"])
else:
    df_cor_api = pd.DataFrame(
        columns=[
            "CORRETOR",
            "CPF_CORRETOR",
            "EMAIL_CORRETOR",
            "TELEFONE_CORRETOR",
            "CRECI_CORRETOR",
            "ANIVERSARIO_CORRETOR",
            "STATUS_CORRETOR",
            "NOTIF_EMAIL",
            "NOTIF_WHATSAPP",
            "NOTIF_PUSH",
        ]
    )

# ---------------------------------------------------------
# 5) TABELA FINAL CONSOLIDADA POR CORRETOR
# ---------------------------------------------------------
df_base = pd.DataFrame({"CORRETOR": corretores_ativos})

df_base = (
    df_base
    .merge(df_kpis_plan, on="CORRETOR", how="left")
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
    .merge(df_cor_api, on="CORRETOR", how="left")
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

df_base = df_base[
    (df_base["DIAS_SEM_MOV"].isna()) | (df_base["DIAS_SEM_MOV"] <= 30)
].reset_index(drop=True)

corretores_final = sorted(df_base["CORRETOR"].unique().tolist())

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

if "ANIVERSARIO_CORRETOR" in df_exibe.columns:
    df_exibe["Aniversário"] = df_exibe["ANIVERSARIO_CORRETOR"].apply(
        lambda d: d.strftime("%d/%m") if pd.notna(d) else "-"
    )
if "CPF_CORRETOR" in df_exibe.columns:
    df_exibe["CPF"] = df_exibe["CPF_CORRETOR"].apply(format_cpf)
if "EMAIL_CORRETOR" in df_exibe.columns:
    df_exibe["E-mail"] = df_exibe["EMAIL_CORRETOR"]
if "TELEFONE_CORRETOR" in df_exibe.columns:
    df_exibe["Telefone"] = df_exibe["TELEFONE_CORRETOR"]
if "CRECI_CORRETOR" in df_exibe.columns:
    df_exibe["CRECI"] = df_exibe["CRECI_CORRETOR"]
if "STATUS_CORRETOR" in df_exibe.columns:
    df_exibe["Status CRM"] = df_exibe["STATUS_CORRETOR"]

df_exibe["Último movimento"] = df_exibe["ULTIMO_MOVIMENTO"].apply(
    lambda d: d.strftime("%d/%m/%Y") if pd.notna(d) else "-"
)
df_exibe["Dias sem movimento"] = df_exibe["DIAS_SEM_MOV"].apply(
    lambda x: int(x) if pd.notna(x) else "-"
)

colunas_ordem = [
    "CORRETOR",
    "CPF",
    "E-mail",
    "Telefone",
    "CRECI",
    "Aniversário",
    "Status CRM",
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

st.title("🧑‍💼 Corretores – Visão Geral")

st.markdown(
    """
Este painel mostra **indicadores completos dos corretores**:

- 📊 Análises, aprovações, reprovações, vendas e VGV (planilha)
- 📥 Leads recebidos (CRM)
- 🕒 Último movimento (planilha + CRM)
- 📆 Presença (dias com ação) e **dias sem ação**
- 🧾 Dados pessoais do corretor (CPF, telefone, e-mail, CRECI, aniversário, status e notificações)
"""
)

st.markdown("### 1️⃣ Tabela consolidada por corretor")

st.dataframe(
    df_exibe,
    use_container_width=True,
    hide_index=True,
)

st.markdown("---")

st.markdown("### 2️⃣ Visão individual por corretor")

corretor_sel = st.selectbox(
    "Corretor (visão individual)",
    options=["Todos"] + corretores_final,
)

if corretor_sel != "Todos" and corretor_sel in df_base["CORRETOR"].values:
    st.markdown("---")
    st.subheader(f"6️⃣ Visão individual – {corretor_sel}")

    linha = df_base[df_base["CORRETOR"] == corretor_sel].iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Leads recebidos", int(linha.get("LEADS", 0)))
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
    ult_mov = linha.get("ULTIMO_MOVIMENTO", pd.NaT)
    dias_sem = linha.get("DIAS_SEM_MOV", np.nan)
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

    # Dados pessoais do corretor (CRM)
    st.markdown("**Dados pessoais do corretor (CRM)**")
    cpf_corr = linha.get("CPF_CORRETOR", None)
    cpf_corr_fmt = format_cpf(cpf_corr) if cpf_corr not in [None, ""] else "-"
    aniv_corr = linha.get("ANIVERSARIO_CORRETOR", None)
    if isinstance(aniv_corr, (datetime, pd.Timestamp, date)):
        aniv_corr_fmt = aniv_corr.strftime("%d/%m")
    elif pd.notna(aniv_corr) if aniv_corr is not None else False:
        try:
            aniv_corr_fmt = pd.to_datetime(aniv_corr, errors="coerce").strftime("%d/%m")
        except Exception:
            aniv_corr_fmt = "-"
    else:
        aniv_corr_fmt = "-"

    c14, c15, c16 = st.columns(3)
    c14.metric("CPF", cpf_corr_fmt)
    c15.metric("Telefone", linha.get("TELEFONE_CORRETOR", "-") or "-")
    c16.metric("Aniversário", aniv_corr_fmt)

    st.write(f"**E-mail:** {linha.get('EMAIL_CORRETOR', '-') or '-'}")
    st.write(f"**CRECI:** {linha.get('CRECI_CORRETOR', '-') or '-'}")

    notif_email = linha.get("NOTIF_EMAIL", "")
    notif_whats = linha.get("NOTIF_WHATSAPP", "")
    notif_push = linha.get("NOTIF_PUSH", "")
    if any([notif_email, notif_whats, notif_push]):
        st.write(
            f"**Notificações CRM:** E-mail: {notif_email or '-'} | "
            f"WhatsApp: {notif_whats or '-'} | Push: {notif_push or '-'}"
        )

    st.info(
        "Movimento considera qualquer atividade na planilha (análises, vendas, etc.) "
        "e qualquer atividade no CRM (captura, primeiro contato ou última interação). "
        "Se em um dia não houve nenhuma dessas ações, o dia conta como **dia sem ação**."
    )
