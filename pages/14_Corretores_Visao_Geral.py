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
    st.sidebar.image("logo_mr.png", use_container_width=True)
except Exception:
    pass

st.title("🧑‍💼 Corretores – Visão Geral (somente corretores ativos no CRM)")
st.caption(
    "KPIs por corretor (análises, aprovações, vendas, leads), tempo sem movimento e faltas "
    "considerando apenas corretores ativos no CRM."
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


# ---------------------------------------------------------
# BASE PLANILHA (MESMA LÓGICA DO APP PRINCIPAL)
# ---------------------------------------------------------
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID_ANALISES = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ANALISES}"


@st.cache_data(ttl=300)
def carregar_planilha():
    df = pd.read_csv(CSV_URL)
    df.columns = [c.upper().strip() for c in df.columns]

    # DIA
    if "DATA" in df.columns:
        df["DIA"] = limpar_data(df["DATA"])
    elif "DIA" in df.columns:
        df["DIA"] = limpar_data(df["DIA"])
    else:
        df["DIA"] = pd.NaT

    # CORRETOR / EQUIPE
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

    # STATUS_BASE
    possiveis_status = ["STATUS", "SITUAÇÃO", "SITUAÇÃO ATUAL", "SITUACAO", "SITUACAO ATUAL"]
    col_status = next((c for c in possiveis_status if c in df.columns), None)

    df["STATUS_BASE"] = ""
    if col_status:
        s = df[col_status].fillna("").astype(str).str.upper()

        df.loc[s.str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA GERADA"
        df.loc[s.str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA INFORMADA"
        df.loc[s.str.contains("APROV"), "STATUS_BASE"] = "APROVADO"
        df.loc[s.str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
        df.loc[s.str.contains("REANÁLISE") | s.str.contains("REANALISE"), "STATUS_BASE"] = "REANÁLISE"
        df.loc[
            (df["STATUS_BASE"] == "")
            & s.str.contains("ANÁLISE")
            & ~s.str.contains("REANÁLISE")
            & ~s.str.contains("REANALISE"),
            "STATUS_BASE",
        ] = "EM ANÁLISE"
    else:
        df["STATUS_BASE"] = "NÃO INFORMADO"

    # NOME / CPF CLIENTE
    possiveis_nomes = ["NOME", "CLIENTE", "NOME CLIENTE", "NOME DO CLIENTE"]
    col_nome = next((c for c in possiveis_nomes if c in df.columns), None)
    if col_nome:
        df["NOME_CLIENTE_BASE"] = (
            df[col_nome]
            .fillna("NÃO INFORMADO")
            .astype(str)
            .str.upper()
            .str.strip()
        )
    else:
        df["NOME_CLIENTE_BASE"] = "NÃO INFORMADO"

    possiveis_cpf = ["CPF", "CPF CLIENTE", "CPF DO CLIENTE"]
    col_cpf = next((c for c in possiveis_cpf if c in df.columns), None)
    if col_cpf:
        df["CPF_CLIENTE_BASE"] = (
            df[col_cpf]
            .fillna("")
            .astype(str)
            .str.replace(r"\D", "", regex=True)
        )
    else:
        df["CPF_CLIENTE_BASE"] = ""

    # VGV
    if "OBSERVAÇÕES" in df.columns:
        df["VGV"] = pd.to_numeric(df["OBSERVAÇÕES"], errors="coerce").fillna(0)
    else:
        df["VGV"] = 0

    return df


df_planilha = carregar_planilha()
if df_planilha.empty:
    st.error("Erro ao carregar a planilha de análises/vendas.")
    st.stop()

# ---------------------------------------------------------
# BASE CRM – df_leads DO SESSION_STATE
# ---------------------------------------------------------
df_leads_raw = st.session_state.get("df_leads", pd.DataFrame())

if df_leads_raw is None or df_leads_raw.empty:
    st.error(
        "Nenhum dado de leads do CRM encontrado. "
        "Abra primeiro a página principal (app_dashboard.py) para carregar os leads."
    )
    st.stop()

df_leads = df_leads_raw.copy()
lower_cols = {c.lower(): c for c in df_leads.columns}


def get_col(possiveis):
    for nome in possiveis:
        if nome in lower_cols:
            return lower_cols[nome]
    return None


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
if col_corretor_crm:
    df_leads["CORRETOR_CRM"] = (
        df_leads[col_corretor_crm]
        .fillna("SEM CORRETOR")
        .astype(str)
        .str.upper()
        .str.strip()
    )
else:
    df_leads["CORRETOR_CRM"] = "SEM CORRETOR"

# Datas do CRM
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

# Última atividade no CRM
df_leads["ULT_ATIVIDADE_CRM"] = df_leads[
    ["DATA_CAPTURA_DT", "DATA_COM_CORRETOR_DT", "DATA_ULT_INTERACAO_DT"]
].max(axis=1)
df_leads["ULT_ATIVIDADE_CRM"] = pd.to_datetime(
    df_leads["ULT_ATIVIDADE_CRM"], errors="coerce"
)

# ---------------------------------------------------------
# FILTROS LATERAIS
# ---------------------------------------------------------
st.sidebar.title("Filtros – Corretores")

dias_validos = df_planilha["DIA"].dropna()
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

# Corretores ativos no CRM (base para tudo)
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

corretor_sel = st.sidebar.selectbox(
    "Corretor (visão individual)",
    options=["Todos"] + corretores_ativos,
)

st.caption(
    f"Período selecionado: **{data_ini.strftime('%d/%m/%Y')}** até **{data_fim.strftime('%d/%m/%Y')}**"
)

# ---------------------------------------------------------
# FILTROS DE PERÍODO – PLANILHA E CRM
# ---------------------------------------------------------
df_plan_periodo = df_planilha[
    (df_planilha["DIA"] >= data_ini) & (df_planilha["DIA"] <= data_fim)
].copy()
df_plan_periodo = df_plan_periodo[df_plan_periodo["CORRETOR"].isin(corretores_ativos)]

df_leads_periodo = df_leads[
    (df_leads["DATA_CAPTURA_DT"].dt.date >= data_ini)
    & (df_leads["DATA_CAPTURA_DT"].dt.date <= data_fim)
].copy()
df_leads_periodo = df_leads_periodo[df_leads_periodo["CORRETOR_CRM"].isin(corretores_ativos)]

# ---------------------------------------------------------
# 1) LISTA DE CORRETORES ATIVOS NO CRM
# ---------------------------------------------------------
st.subheader("1️⃣ Corretores ativos no CRM (base para os KPIs)")

df_cor_ativos = pd.DataFrame({"CORRETOR": corretores_ativos})
st.dataframe(df_cor_ativos, use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# 2) KPIs PLANILHA – ANÁLISES / APROVAÇÕES / VENDAS
# ---------------------------------------------------------
st.subheader("2️⃣ KPIs da planilha – análises, aprovações e vendas")

def conta_analises(serie_status):
    s = serie_status.fillna("")
    return ((s == "EM ANÁLISE") | (s == "REANÁLISE")).sum()

df_analises = (
    df_plan_periodo.groupby("CORRETOR", dropna=False)["STATUS_BASE"]
    .agg(
        ANALISES=conta_analises,
        APROVACOES=lambda s: (s == "APROVADO").sum(),
        REPROVACOES=lambda s: (s == "REPROVADO").sum(),
    )
    .reset_index()
)

# Vendas (com regra de venda informada x gerada)
df_vendas_ref = df_plan_periodo[
    df_plan_periodo["STATUS_BASE"].isin(["VENDA GERADA", "VENDA INFORMADA"])
].copy()

if not df_vendas_ref.empty:
    df_vendas_ref["CHAVE_CLIENTE"] = (
        df_vendas_ref["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO")
        + " | "
        + df_vendas_ref["CPF_CLIENTE_BASE"].fillna("")
    )

    df_vendas_ref = df_vendas_ref.sort_values("DIA")
    df_vendas_ult = df_vendas_ref.groupby("CHAVE_CLIENTE", as_index=False).tail(1)

    if tipo_venda == "GERADAS + INFORMADAS":
        mask_venda = df_vendas_ult["STATUS_BASE"].isin(
            ["VENDA GERADA", "VENDA INFORMADA"]
        )
    elif tipo_venda == "Apenas GERADAS":
        mask_venda = df_vendas_ult["STATUS_BASE"].eq("VENDA GERADA")
    else:  # Apenas INFORMADAS
        mask_venda = df_vendas_ult["STATUS_BASE"].eq("VENDA INFORMADA")

    df_vendas_final = df_vendas_ult[mask_venda].copy()

    df_vendas_kpi = (
        df_vendas_final.groupby("CORRETOR", dropna=False)
        .agg(
            VENDAS=("CHAVE_CLIENTE", "nunique"),
            VGV=("VGV", "sum"),
        )
        .reset_index()
    )
else:
    df_vendas_kpi = pd.DataFrame(columns=["CORRETOR", "VENDAS", "VGV"])

df_kpis_plan = pd.merge(
    df_analises,
    df_vendas_kpi,
    on="CORRETOR",
    how="outer",
).fillna(0)

df_kpis_plan["VGV"] = df_kpis_plan["VGV"].astype(float)
df_kpis_plan["VENDAS"] = df_kpis_plan["VENDAS"].astype(int)

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
# 3) LEADS RECEBIDOS POR CORRETOR (PERÍODO)
# ---------------------------------------------------------
st.subheader("3️⃣ Leads recebidos no período (CRM)")

if df_leads_periodo.empty:
    st.info("Nenhum lead recebido no período para os corretores ativos no CRM.")
    df_leads_count = pd.DataFrame(columns=["CORRETOR", "LEADS"])
else:
    df_leads_count = (
        df_leads_periodo.groupby("CORRETOR_CRM", dropna=False)
        .size()
        .reset_index(name="LEADS")
        .rename(columns={"CORRETOR_CRM": "CORRETOR"})
    )

st.dataframe(df_leads_count, use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# 4) MOVIMENTO E FALTAS POR CORRETOR
# ---------------------------------------------------------
st.subheader("4️⃣ Movimento e faltas por corretor")

hoje = date.today()

# --------- ÚLTIMO MOVIMENTO NA PLANILHA (SEM groupby.max) ---------
tmp_plan = (
    df_planilha[df_planilha["CORRETOR"].isin(corretores_ativos)]
    .dropna(subset=["DIA"])
    .copy()
)
tmp_plan = tmp_plan.sort_values(["CORRETOR", "DIA"])
df_ult_plan = tmp_plan.drop_duplicates(subset=["CORRETOR"], keep="last")[
    ["CORRETOR", "DIA"]
].rename(columns={"DIA": "ULT_MOV_PLAN"})

# --------- ÚLTIMO MOVIMENTO NO CRM (SEM groupby.max) ---------
df_leads_val = df_leads[df_leads["CORRETOR_CRM"].isin(corretores_ativos)].copy()
df_leads_val["ULT_ATIVIDADE_CRM"] = pd.to_datetime(
    df_leads_val["ULT_ATIVIDADE_CRM"], errors="coerce"
)

if df_leads_val["ULT_ATIVIDADE_CRM"].notna().any():
    tmp_crm = df_leads_val.dropna(subset=["ULT_ATIVIDADE_CRM"]).copy()
    tmp_crm["DATA_ULT"] = tmp_crm["ULT_ATIVIDADE_CRM"].dt.date
    tmp_crm = tmp_crm.sort_values(["CORRETOR_CRM", "DATA_ULT"])
    df_ult_crm = tmp_crm.drop_duplicates(
        subset=["CORRETOR_CRM"], keep="last"
    )[
        ["CORRETOR_CRM", "DATA_ULT"]
    ].rename(
        columns={
            "CORRETOR_CRM": "CORRETOR",
            "DATA_ULT": "ULT_MOV_CRM",
        }
    )
else:
    df_ult_crm = pd.DataFrame(columns=["CORRETOR", "ULT_MOV_CRM"])

# Junta últimas datas
df_ult_mov = pd.merge(df_ult_plan, df_ult_crm, on="CORRETOR", how="outer")

def pick_max(row):
    datas = []
    if pd.notna(row.get("ULT_MOV_PLAN")):
        datas.append(row.get("ULT_MOV_PLAN"))
    if pd.notna(row.get("ULT_MOV_CRM")):
        datas.append(row.get("ULT_MOV_CRM"))
    if not datas:
        return pd.NaT
    return max(datas)

df_ult_mov["ULTIMO_MOVIMENTO"] = df_ult_mov.apply(pick_max, axis=1)
df_ult_mov["DIAS_SEM_MOV"] = df_ult_mov["ULTIMO_MOVIMENTO"].apply(
    lambda d: (hoje - d).days if pd.notna(d) else None
)

# --------- PRESENÇA / FALTAS POR DIA ---------
df_pres_plan = (
    df_plan_periodo[["CORRETOR", "DIA"]].dropna().drop_duplicates().copy()
)
df_pres_plan["PRESENTE"] = True

dfs_crm_pres = []
for col in ["DATA_CAPTURA_DT", "DATA_COM_CORRETOR_DT", "DATA_ULT_INTERACAO_DT"]:
    if col in df_leads_val.columns:
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
    [df_pres_plan, df_pres_crm],
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
df_grid["FALTA"] = ~df_grid["PRESENTE"]

df_faltas = (
    df_grid.groupby("CORRETOR", dropna=False)["FALTA"]
    .sum()
    .reset_index()
    .rename(columns={"FALTA": "FALTAS"})
)
df_faltas["TOTAL_DIAS"] = len(dias_range)
df_faltas["DIAS_PRESENTE"] = df_faltas["TOTAL_DIAS"] - df_faltas["FALTAS"]
df_faltas["PRESENCA_PCT"] = np.where(
    df_faltas["TOTAL_DIAS"] > 0,
    df_faltas["DIAS_PRESENTE"] / df_faltas["TOTAL_DIAS"] * 100,
    0,
)

# ---------------------------------------------------------
# 5) TABELA FINAL CONSOLIDADA POR CORRETOR
# ---------------------------------------------------------
df_base = pd.DataFrame({"CORRETOR": corretores_ativos})

df_base = (
    df_base
    .merge(df_kpis_plan, on="CORRETOR", how="left")
    .merge(df_leads_count, on="CORRETOR", how="left")
    .merge(df_ult_mov[["CORRETOR", "ULTIMO_MOVIMENTO", "DIAS_SEM_MOV"]], on="CORRETOR", how="left")
    .merge(df_faltas[["CORRETOR", "FALTAS", "TOTAL_DIAS", "DIAS_PRESENTE", "PRESENCA_PCT"]], on="CORRETOR", how="left")
)

for col in ["ANALISES", "APROVACOES", "REPROVACOES", "VENDAS", "LEADS", "FALTAS", "TOTAL_DIAS", "DIAS_PRESENTE"]:
    if col in df_base.columns:
        df_base[col] = df_base[col].fillna(0).astype(int)

for col in ["VGV", "TICKET_MEDIO", "TAXA_APROV_ANALISE", "TAXA_VENDA_ANALISE", "TAXA_VENDA_APROV", "PRESENCA_PCT"]:
    if col in df_base.columns:
        df_base[col] = df_base[col].fillna(0).astype(float)

df_exibe = df_base.copy()
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
    "FALTAS",
    "TOTAL_DIAS",
    "Presença (%)",
    "Último movimento",
    "Dias sem movimento",
]
colunas_ordem = [c for c in colunas_ordem if c in df_exibe.columns]

st.subheader("5️⃣ Visão geral consolidada por corretor")
st.dataframe(
    df_exibe[colunas_ordem].sort_values("CORRETOR"),
    use_container_width=True,
    hide_index=True,
)

# ---------------------------------------------------------
# 6) VISÃO INDIVIDUAL – CARDS POR CORRETOR
# ---------------------------------------------------------
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
        "Leads/dia (média)",
        (
            f"{linha.get('LEADS', 0) / linha.get('TOTAL_DIAS', 1):.1f}"
            if linha.get("TOTAL_DIAS", 0) > 0
            else "-"
        ),
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
        "Faltas no período",
        int(linha.get("FALTAS", 0)),
    )

    st.info(
        "Movimento considera qualquer atividade na planilha (análises, vendas, etc.) "
        "e qualquer atividade no CRM (captura, primeiro contato ou última interação). "
        "Se em um dia não houve nenhuma dessas ações, o dia conta como **falta**."
    )
