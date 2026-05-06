import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from fpdf import FPDF


if "logado" not in st.session_state or not st.session_state.logado:
    st.warning("🔒 Acesso restrito. Faça login para continuar.")
    st.stop()
# ---------------------------------------------------------
# PERFIL / USUÁRIO (para trava de acesso)
# ---------------------------------------------------------
perfil = str(st.session_state.get("perfil", "")).lower().strip()
nome_usuario = str(st.session_state.get("nome_usuario", "")).upper().strip()

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
    "KPIs por corretor (análises, aprovações, vendas, leads), tempo sem movimento e dias sem ação "
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
def limpar_texto_pdf(texto):
    if pd.isna(texto):
        return ""
    return (
        str(texto)
        .encode("latin-1", errors="ignore")
        .decode("latin-1")
    )


def gerar_pdf(df_pdf):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=10)

    linhas_por_pagina = 33
    col_nome = 70
    col_tel = 40
    col_obs = 80

    for i in range(0, len(df_pdf), linhas_por_pagina):
        pdf.add_page()
        pdf.set_font("Arial", "B", 10)

        pdf.cell(col_nome, 8, "NOME", border=1)
        pdf.cell(col_tel, 8, "TELEFONE", border=1)
        pdf.cell(col_obs, 8, "INFORMAÇÕES", border=1)
        pdf.ln()

        pdf.set_font("Arial", size=9)

        bloco = df_pdf.iloc[i:i + linhas_por_pagina]

        for _, row in bloco.iterrows():
            nome = limpar_texto_pdf(row["NOME"])
            telefone = limpar_texto_pdf(row["TELEFONE"])

            pdf.cell(col_nome, 8, nome[:40], border=1)
            pdf.cell(col_tel, 8, telefone[:20], border=1)
            pdf.cell(col_obs, 8, "", border=1)
            pdf.ln()

    return bytes(pdf.output(dest="S"))


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
                .fillna("SEM CORRETOR")
                .astype(str)
                .str.upper()
                .str.strip()
            )

    if "CORRETOR" not in df.columns:
        df["CORRETOR"] = "SEM CORRETOR"

    # STATUS / SITUAÇÃO
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
        df.loc[s.str.contains("DESIST"), "STATUS_BASE"] = "DESISTIU"

    # NOME CLIENTE
    possiveis_nome = ["CLIENTE", "NOME CLIENTE", "NOME DO CLIENTE"]
    col_nome = next((c for c in possiveis_nome if c in df.columns), None)
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

    # CPF CLIENTE
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

    # 🔑 CHAVE_CLIENTE global
    df["CHAVE_CLIENTE"] = (
        df["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
        + " | "
        + df["CPF_CLIENTE_BASE"].fillna("").astype(str).str.strip()
    )

    # VGV
    if "OBSERVAÇÕES" in df.columns:
        df["VGV"] = pd.to_numeric(df["OBSERVAÇÕES"], errors="coerce").fillna(0)
    else:
        df["VGV"] = 0.0

    return df


df_planilha = carregar_planilha()
if df_planilha.empty:
    st.error("Erro ao carregar a planilha de análises/vendas.")
    st.stop()

# Normaliza STATUS_BASE pra garantir DESISTIU maiúsculo
df_planilha["STATUS_BASE"] = df_planilha["STATUS_BASE"].fillna("").astype(str).str.upper()
df_planilha.loc[
    df_planilha["STATUS_BASE"].str.contains("DESIST", na=False), "STATUS_BASE"
] = "DESISTIU"

# 🔥 STATUS FINAL GLOBAL POR CLIENTE (regra do DESISTIU)
df_ordenado_global = df_planilha.sort_values("DIA")
status_final_por_cliente = (
    df_ordenado_global.groupby("CHAVE_CLIENTE")["STATUS_BASE"].last().fillna("")
)
status_final_por_cliente = status_final_por_cliente.astype(str).str.upper()
status_final_por_cliente.name = "STATUS_FINAL_CLIENTE"

# ---------------------------------------------------------
# BASE CRM – df_leads DO SESSION_STATE
# ---------------------------------------------------------
df_leads_raw = st.session_state.get("df_leads", pd.DataFrame())

if df_leads_raw is None or df_leads_raw.empty:
    st.warning(
        "Nenhum dado de leads do CRM encontrado na sessão. "
        "Os indicadores de leads e movimento no CRM serão considerados como zero."
    )
    df_leads = pd.DataFrame()
else:
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

col_data_com_cor = get_col(["data_com_corretor", "data_primeiro_contato"])
if col_data_com_cor:
    df_leads["DATA_COM_CORRETOR_DT"] = pd.to_datetime(
        df_leads[col_data_com_cor], errors="coerce"
    )
else:
    df_leads["DATA_COM_CORRETOR_DT"] = pd.NaT

col_data_ult_inter = get_col(["data_ultima_interacao", "data_ult_interacao"])
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

# ---------------------------------------------------------
# 1) LISTA DE CORRETORES ATIVOS NO CRM
# ---------------------------------------------------------
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
# ---------------------------------------------------------
# 🔒 TRAVA — CORRETOR VÊ APENAS OS PRÓPRIOS NÚMEROS
# ---------------------------------------------------------
if perfil == "corretor" and nome_usuario:
    # força lista de corretores para apenas ele
    corretores_ativos = [nome_usuario]

    # filtra planilha para o corretor logado
    if "CORRETOR" in df_planilha.columns:
        df_planilha = df_planilha[
            df_planilha["CORRETOR"].astype(str).str.upper().str.strip() == nome_usuario
        ].copy()

    # filtra CRM (se existir)
    if "CORRETOR_CRM" in df_leads.columns:
        df_leads = df_leads[
            df_leads["CORRETOR_CRM"].astype(str).str.upper().str.strip() == nome_usuario
        ].copy()

# ---------------------------------------------------------
# FILTROS DE PERÍODO – PLANILHA E CRM
# ---------------------------------------------------------
df_plan_periodo = df_planilha[
    (df_planilha["DIA"] >= data_ini) & (df_planilha["DIA"] <= data_fim)
].copy()

if not df_leads.empty and "DATA_CAPTURA_DT" in df_leads.columns:
    df_leads_periodo = df_leads[
        (df_leads["DATA_CAPTURA_DT"].dt.date >= data_ini)
        & (df_leads["DATA_CAPTURA_DT"].dt.date <= data_fim)
    ].copy()
else:
    df_leads_periodo = pd.DataFrame()
# ---------------------------------------------------------
# NORMALIZA CAMPOS DO CRM (MESMA LÓGICA DA OFERTA ATIVA)
# ---------------------------------------------------------
if not df_leads_periodo.empty:
    df_leads_periodo["NOME"] = (
        df_leads_periodo.get("nome_pessoa", "")
        .fillna("")
        .astype(str)
        .str.upper()
        .str.strip()
    )

    df_leads_periodo["TELEFONE"] = (
        df_leads_periodo.get("telefone_pessoa", "")
        .fillna("")
        .astype(str)
        .str.strip()
    )

# ---------------------------------------------------------
# NORMALIZA CAMPOS DO CRM (MESMA LÓGICA DA OFERTA ATIVA)
# ---------------------------------------------------------
if not df_leads_periodo.empty:
    df_leads_periodo["NOME"] = (
        df_leads_periodo.get("nome_pessoa", "")
        .fillna("")
        .astype(str)
        .str.upper()
        .str.strip()
    )

    df_leads_periodo["TELEFONE"] = (
        df_leads_periodo.get("telefone_pessoa", "")
        .fillna("")
        .astype(str)
        .str.strip()
    )

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

# 🔥 Vendas (com regra DESISTIU global)
df_vendas_ref = df_plan_periodo[
    df_plan_periodo["STATUS_BASE"].isin(["VENDA GERADA", "VENDA INFORMADA"])
].copy()

if not df_vendas_ref.empty:
    # garante CHAVE_CLIENTE para esse subconjunto
    if "CHAVE_CLIENTE" not in df_vendas_ref.columns:
        df_vendas_ref["CHAVE_CLIENTE"] = (
            df_vendas_ref["NOME_CLIENTE_BASE"]
            .fillna("NÃO INFORMADO")
            .astype(str)
            .str.upper()
            .str.strip()
            + " | "
            + df_vendas_ref["CPF_CLIENTE_BASE"].fillna("").astype(str).str.strip()
        )

    # junta STATUS_FINAL_CLIENTE (global)
    df_vendas_ref = df_vendas_ref.merge(
        status_final_por_cliente,
        on="CHAVE_CLIENTE",
        how="left",
    )

    # remove clientes cujo status final global é DESISTIU
    df_vendas_ref = df_vendas_ref[df_vendas_ref["STATUS_FINAL_CLIENTE"] != "DESISTIU"]

    if not df_vendas_ref.empty:
        # pega só o último registro por cliente dentro do período
        df_vendas_ref = df_vendas_ref.sort_values(["CHAVE_CLIENTE", "DIA"])
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

st.dataframe(
    df_kpis_plan[
        [
            "CORRETOR",
            "ANALISES",
            "APROVACOES",
            "REPROVACOES",
            "VENDAS",
            "VGV",
            "TICKET_MEDIO",
            "TAXA_APROV_ANALISE",
            "TAXA_VENDA_ANALISE",
            "TAXA_VENDA_APROV",
        ]
    ],
    use_container_width=True,
    hide_index=True,
)

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
# 4) MOVIMENTO E DIAS SEM AÇÃO POR CORRETOR
# ---------------------------------------------------------
st.subheader("4️⃣ Movimento e dias sem ação por corretor")

hoje = date.today()

# ---- Último movimento na planilha (sem groupby.max) ----
tmp_plan = (
    df_planilha[df_planilha["CORRETOR"].isin(corretores_ativos)]
    .dropna(subset=["DIA"])
    .copy()
)
tmp_plan = tmp_plan.sort_values(["CORRETOR", "DIA"])
df_ult_plan = tmp_plan.drop_duplicates(subset=["CORRETOR"], keep="last")[
    ["CORRETOR", "DIA"]
].rename(columns={"DIA": "ULT_MOV_PLAN"})

# ---- Último movimento no CRM (sem groupby.max) ----
df_leads_val = df_leads[df_leads["CORRETOR_CRM"].isin(corretores_ativos)].copy()
if not df_leads_val.empty and df_leads_val["ULT_ATIVIDADE_CRM"].notna().any():
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

# junta últimos movimentos
df_ult_mov = pd.merge(
    pd.DataFrame({"CORRETOR": corretores_ativos}),
    df_ult_plan,
    on="CORRETOR",
    how="left",
)

df_ult_mov = pd.merge(
    df_ult_mov,
    df_ult_crm,
    on="CORRETOR",
    how="left",
)


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

# ---- Presença / dias sem ação por dia ----
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

df_presenca = pd.concat(
    [
        df_pres_plan[["CORRETOR", "DIA", "PRESENTE"]],
        df_pres_crm[["CORRETOR", "DIA", "PRESENTE"]],
    ],
    ignore_index=True,
)

df_presenca = df_presenca.drop_duplicates(subset=["CORRETOR", "DIA"])

dias_range = pd.date_range(start=data_ini, end=data_fim, freq="D").date
grid_index = pd.MultiIndex.from_product(
    [corretores_ativos, dias_range], names=["CORRETOR", "DIA"]
)
df_grid = pd.DataFrame(index=grid_index).reset_index()

df_grid = df_grid.merge(
    df_presenca, on=["CORRETOR", "DIA"], how="left"
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

df_movimento = pd.merge(
    df_ult_mov[["CORRETOR", "ULTIMO_MOVIMENTO", "DIAS_SEM_MOV"]],
    df_faltas,
    on="CORRETOR",
    how="left",
).fillna({"FALTAS": 0, "TOTAL_DIAS": 0})

df_movimento["ULTIMO_MOVIMENTO_STR"] = df_movimento["ULTIMO_MOVIMENTO"].apply(
    lambda d: d.strftime("%d/%m/%Y") if pd.notna(d) else "-"
)

st.dataframe(
    df_movimento[
        [
            "CORRETOR",
            "ULTIMO_MOVIMENTO_STR",
            "DIAS_SEM_MOV",
            "FALTAS",
            "TOTAL_DIAS",
        ]
    ].rename(
        columns={
            "ULTIMO_MOVIMENTO_STR": "Último movimento",
            "DIAS_SEM_MOV": "Dias sem movimento",
            "FALTAS": "Dias sem ação",
        }
    ),
    use_container_width=True,
    hide_index=True,
)

# ---------------------------------------------------------
# 5) VISÃO GERAL CONSOLIDADA (JUNTA TUDO)
# ---------------------------------------------------------
df_exibe = pd.merge(
    df_kpis_plan,
    df_leads_count,
    on="CORRETOR",
    how="left",
).merge(
    df_movimento,
    on="CORRETOR",
    how="left",
)

df_exibe["LEADS"] = df_exibe["LEADS"].fillna(0).astype(int)

df_exibe["Ticket médio"] = df_exibe["TICKET_MEDIO"].apply(format_currency)
df_exibe["VGV"] = df_exibe["VGV"].apply(format_currency)

df_exibe["Taxa aprov./análises (%)"] = df_exibe["TAXA_APROV_ANALISE"].round(1)
df_exibe["Taxa vendas/análises (%)"] = df_exibe["TAXA_VENDA_ANALISE"].round(1)
df_exibe["Taxa vendas/aprovações (%)"] = df_exibe["TAXA_VENDA_APROV"].round(1)

df_exibe["Dias sem ação"] = df_exibe["FALTAS"].fillna(0).astype(int)

df_exibe["Presença (%)"] = np.where(
    df_exibe["TOTAL_DIAS"] > 0,
    (df_exibe["TOTAL_DIAS"] - df_exibe["FALTAS"]) / df_exibe["TOTAL_DIAS"] * 100,
    np.nan,
).round(1)

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

st.subheader("5️⃣ Visão geral consolidada por corretor")
st.dataframe(
    df_exibe[colunas_ordem].sort_values("CORRETOR"),
    use_container_width=True,
    hide_index=True,
)

# ---------------------------------------------------------
# 6) DETALHE DE UM CORRETOR (OPCIONAL)
# ---------------------------------------------------------
st.subheader("6️⃣ Detalhe de um corretor (opcional)")

if perfil == "corretor" and nome_usuario:
    corretor_sel = st.selectbox(
        "Selecione um corretor para ver o detalhe:",
        options=[nome_usuario],
        index=0,
        disabled=True,
    )
else:
    corretor_sel = st.selectbox(
        "Selecione um corretor para ver o detalhe:",
        options=[""] + corretores_ativos,
        index=0,
    )

if corretor_sel:
    linha = df_exibe[df_exibe["CORRETOR"] == corretor_sel].iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Leads", int(linha.get("LEADS", 0)))
    c2.metric("Análises", int(linha.get("ANALISES", 0)))
    c3.metric("Aprovações", int(linha.get("APROVACOES", 0)))
    c4.metric("Reprovações", int(linha.get("REPROVACOES", 0)))
# ---------------------------------------------------------
# PDF DE LEADS DO CORRETOR (mesmo período do filtro)
# ---------------------------------------------------------
df_leads_do_corretor = pd.DataFrame()

if not df_leads_periodo.empty and "CORRETOR_CRM" in df_leads_periodo.columns:
    df_leads_do_corretor = df_leads_periodo[
        df_leads_periodo["CORRETOR_CRM"].astype(str).str.upper().str.strip() == corretor_sel
    ].copy()
if not corretor_sel:

    st.info("Selecione um corretor acima para gerar o PDF de leads.")
if corretor_sel:
    with c1:
        if df_leads_do_corretor.empty:
            st.caption("Sem leads do CRM no período.")
        else:
            df_pdf = pd.DataFrame({
                "NOME": df_leads_do_corretor["NOME"].fillna("").astype(str).str.upper().str.strip(),
                "TELEFONE": df_leads_do_corretor["TELEFONE"].fillna("").astype(str).str.strip(),
                "INFORMAÇÕES": ""
            })

            pdf_bytes = gerar_pdf(df_pdf)

            st.download_button(
                label="📄 Gerar PDF de Leads",
                data=pdf_bytes,
                file_name=f"leads_{corretor_sel.replace(' ', '_')}.pdf",
                mime="application/pdf",
            )

 
    # ---------------------------------------------------------
    # BOTÃO: GERAR PDF DOS LEADS (CRM) DO CORRETOR NO PERÍODO
    # - usa df_leads_periodo (já filtrado por data_ini/data_fim)
    # - filtra por CORRETOR_CRM == corretor_sel
    # - PDF com 3 colunas: NOME | TELEFONE | INFORMAÇÕES (vazia)
    # ---------------------------------------------------------
    df_leads_do_corretor = pd.DataFrame()
    if "CORRETOR_CRM" in df_leads_periodo.columns and not df_leads_periodo.empty:
        df_leads_do_corretor = df_leads_periodo[
            df_leads_periodo["CORRETOR_CRM"].astype(str).str.upper().str.strip() == corretor_sel
        ].copy()

    # tenta achar colunas de nome e telefone no df_leads (sem achismo: só varredura por nomes comuns)
    col_nome_lead = get_col(["nome", "nome_lead", "nome_cliente", "cliente", "lead"])
    col_tel_lead = get_col(["telefone", "celular", "fone", "whatsapp", "phone"])

    with c1:
        if df_leads_do_corretor.empty:
            st.caption("Sem leads do CRM no período para gerar PDF.")
        elif not col_nome_lead or not col_tel_lead:
            st.caption("Não encontrei colunas de NOME/TELEFONE no retorno do CRM.")
        else:
            df_pdf = pd.DataFrame({
                "NOME": df_leads_do_corretor[col_nome_lead].fillna("").astype(str).str.upper().str.strip(),
                "TELEFONE": df_leads_do_corretor[col_tel_lead].fillna("").astype(str).str.strip(),
                "INFORMAÇÕES": ""
            })

            titulo_pdf = f"LEADS - {corretor_sel} ({data_ini.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')})"
            pdf_buffer = gerar_pdf_leads_tabela(df_pdf, titulo_pdf)

            st.download_button(
                "Gerar PDF de Leads",
                data=pdf_buffer,
                file_name=f"leads_{corretor_sel.replace(' ', '_')}_{data_ini.strftime('%d%m%Y')}_{data_fim.strftime('%d%m%Y')}.pdf",
                mime="application/pdf",
            )

    c5, c6, c7 = st.columns(3)
    c5.metric("Vendas", int(linha.get("VENDAS", 0)))
    c6.metric("VGV", format_currency(linha.get("VGV_RAW", 0)))
    c7.metric(
        "Ticket médio (R$)",
        format_currency(linha.get("TICKET_MEDIO", 0)),
    )

    c8, c9, c10 = st.columns(3)
    c8.metric(
        "Taxa aprov./análises (%)",
        f"{linha.get('TAXA_APROV_ANALISE', 0):.1f}",
    )
    c9.metric(
        "Taxa vendas/análises (%)",
        f"{linha.get('TAXA_VENDA_ANALISE', 0):.1f}",
    )
    c10.metric(
        "Taxa vendas/aprovações (%)",
        f"{linha.get('TAXA_VENDA_APROV', 0):.1f}",
    )

    c11, c12, c13 = st.columns(3)
    c11.metric("Último movimento", linha.get("Último movimento", "-"))
    dias_sem = linha.get("DIAS_SEM_MOV", np.nan)
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
