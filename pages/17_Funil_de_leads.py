# =========================================================
# FUNIL DE LEADS – ORIGEM, STATUS E CONVERSÃO
# =========================================================

import streamlit as st
import pandas as pd
import requests
from datetime import date
from utils.supremo_config import TOKEN_SUPREMO

# =========================================================
# CONFIGURAÇÃO
# =========================================================
st.set_page_config(
    page_title="Funil de Leads",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Funil de Leads – Origem, Status e Conversão")

# =========================================================
# PLANILHA
# =========================================================
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

# =========================================================
# UTILIDADES
# =========================================================
MESES = {
    "JANEIRO": 1, "FEVEREIRO": 2, "MARÇO": 3, "MARCO": 3,
    "ABRIL": 4, "MAIO": 5, "JUNHO": 6, "JULHO": 7,
    "AGOSTO": 8, "SETEMBRO": 9, "OUTUBRO": 10,
    "NOVEMBRO": 11, "DEZEMBRO": 12,
}

def parse_data(col):
    return pd.to_datetime(col, dayfirst=True, errors="coerce")

def parse_data_base(label):
    if pd.isna(label):
        return pd.NaT
    p = str(label).upper().split()
    if len(p) < 2:
        return pd.NaT
    mes = MESES.get(p[0])
    try:
        ano = int(p[-1])
    except:
        return pd.NaT
    if not mes:
        return pd.NaT
    return date(ano, mes, 1)

# =========================================================
# CARGA PLANILHA
# =========================================================
@st.cache_data(ttl=300)
def carregar_planilha():
    df = pd.read_csv(CSV_URL, dtype=str)
    df.columns = df.columns.str.upper().str.strip()

    for col in ["CLIENTE", "CORRETOR", "EQUIPE", "SITUAÇÃO", "DATA"]:
        if col not in df.columns:
            df[col] = ""

    df["DATA"] = parse_data(df["DATA"])
    df = df.dropna(subset=["DATA"])

    df["DATA_BASE_LABEL"] = df.get("DATA BASE", "").astype(str).str.strip()
    df["DATA_BASE_DATE"] = df["DATA_BASE_LABEL"].apply(parse_data_base)

    for col in ["CLIENTE", "CORRETOR", "EQUIPE"]:
        df[col] = df[col].astype(str).str.upper().str.strip()

    df["STATUS_RAW"] = df["SITUAÇÃO"].astype(str).str.upper().str.strip()
    df["STATUS_BASE"] = ""

    regras = [
        ("APROVADO BACEN", "APROVADO_BACEN"),
        ("EM ANÁLISE", "ANALISE"),
        ("REANÁLISE", "REANALISE"),
        ("VENDA GERADA", "VENDA_GERADA"),
        ("VENDA INFORMADA", "VENDA_INFORMADA"),
        ("REPROV", "REPROVADO"),
        ("PEND", "PENDENCIA"),
        ("DESIST", "DESISTIU"),
        ("APROVA", "APROVADO"),
    ]

    for chave, valor in regras:
        mask = df["STATUS_RAW"].str.contains(chave, na=False)
        df.loc[mask & (df["STATUS_BASE"] == ""), "STATUS_BASE"] = valor

    return df[df["STATUS_BASE"] != ""]

# =========================================================
# CARGA CRM
# =========================================================
@st.cache_data(ttl=1800)
def carregar_crm():
    url = "https://api.supremocrm.com.br/v1/leads"
    headers = {"Authorization": f"Bearer {TOKEN_SUPREMO}"}

    dados, pagina = [], 1
    while len(dados) < 1000:
        r = requests.get(url, headers=headers, params={"pagina": pagina}, timeout=20)
        if r.status_code != 200:
            break
        js = r.json()
        if not js.get("data"):
            break
        dados.extend(js["data"])
        pagina += 1

    if not dados:
        return pd.DataFrame(columns=["CLIENTE", "ORIGEM", "CAMPANHA", "DATA_CRM"])

    df = pd.DataFrame(dados)

    df["CLIENTE"] = df["nome_pessoa"].astype(str).str.upper().str.strip()

    df["ORIGEM"] = df.get("nome_origem")
    df["ORIGEM"] = df["ORIGEM"].fillna("SEM CADASTRO NO CRM").astype(str).str.upper().str.strip()

    df["CAMPANHA"] = df.get("nome_campanha")
    df["CAMPANHA"] = df["CAMPANHA"].fillna("-").astype(str).str.upper().str.strip()

    df["DATA_CRM"] = pd.to_datetime(df.get("data_captura"), errors="coerce")

    return df[["CLIENTE", "ORIGEM", "CAMPANHA", "DATA_CRM"]]



# =========================================================
# DATASETS
# =========================================================
df_hist = carregar_planilha()
df_crm = carregar_crm()

df_hist = df_hist.merge(df_crm, on="CLIENTE", how="left")
df_hist["ORIGEM"] = df_hist["ORIGEM"].fillna("SEM CADASTRO NO CRM")
df_hist["CAMPANHA"] = df_hist["CAMPANHA"].fillna("-")
# =========================================================
# CRM BASE (CÓPIA PARA FILTROS)
# =========================================================
df_crm_f = df_crm.copy()

# =========================================================
# CRM ENRIQUECIDO COM EQUIPE E CORRETOR (SEM STATUS)
# =========================================================
df_crm_enriquecido = (
    df_crm_f
    .merge(
        df_hist[["CLIENTE", "EQUIPE", "CORRETOR"]],
        on="CLIENTE",
        how="left"
    )
)

df_crm_enriquecido["EQUIPE"] = df_crm_enriquecido["EQUIPE"].fillna("SEM EQUIPE")
df_crm_enriquecido["CORRETOR"] = df_crm_enriquecido["CORRETOR"].fillna("SEM CORRETOR")


# =========================================================
# FILTROS
# =========================================================
st.sidebar.header("Filtros")

modo = st.sidebar.radio("Modo de período", ["DIA", "DATA BASE"])
df_f = df_hist.copy()

if modo == "DIA":
    ini, fim = st.sidebar.date_input(
        "Período",
        value=(df_f["DATA"].min().date(), df_f["DATA"].max().date())
    )
    df_f = df_f[(df_f["DATA"].dt.date >= ini) & (df_f["DATA"].dt.date <= fim)]
else:
    bases = sorted(df_f["DATA_BASE_LABEL"].dropna().unique(), key=parse_data_base)
    sel = st.sidebar.multiselect("Data Base", bases, default=bases)
    if sel:
        df_f = df_f[df_f["DATA_BASE_LABEL"].isin(sel)]
    # =========================================================
# FILTRO POR EQUIPE
# =========================================================
equipes = ["TODAS"] + sorted(df_f["EQUIPE"].dropna().unique())

equipe_sel = st.sidebar.selectbox(
    "Equipe",
    equipes,
    key="filtro_equipe"
)

if equipe_sel != "TODAS":
    df_f = df_f[df_f["EQUIPE"] == equipe_sel]


# =========================================================
# FILTRO POR CORRETOR
# =========================================================
corretores = ["TODOS"] + sorted(df_f["CORRETOR"].dropna().unique())
corretor_sel = st.sidebar.selectbox("Corretor", corretores, key="filtro_corretor")

if corretor_sel != "TODOS":
    df_f = df_f[df_f["CORRETOR"] == corretor_sel]


if equipe_sel != "TODAS":
    df_f = df_f[df_f["EQUIPE"] == equipe_sel]


if corretor_sel != "TODOS":
    df_f = df_f[df_f["CORRETOR"] == corretor_sel]

# =========================================================
# CRM FILTRADO PELO PERÍODO SELECIONADO (DIA ou DATA BASE)
# =========================================================
df_crm_f = df_crm.copy()

if modo == "DIA":
    df_crm_f = df_crm_f[
        (df_crm_f["DATA_CRM"].dt.date >= ini) &
        (df_crm_f["DATA_CRM"].dt.date <= fim)
    ]
else:
    if sel:
        base_df = df_hist[df_hist["DATA_BASE_LABEL"].isin(sel)]
        dt_ini = base_df["DATA"].min()
        dt_fim = base_df["DATA"].max()

        if pd.notna(dt_ini) and pd.notna(dt_fim):
            df_crm_f = df_crm_f[
                (df_crm_f["DATA_CRM"] >= dt_ini) &
                (df_crm_f["DATA_CRM"] <= dt_fim)
            ]

# =========================================================
# SELETOR DE STATUS ATUAL
# =========================================================
 # =========================================================
# SELETOR DE STATUS ATUAL (DINÂMICO – STATUS_BASE)
# =========================================================
# =========================================
# SELETOR – SITUAÇÃO DO LEAD (PLANILHA)
# =========================================
df_base = df_f.copy()


# =========================================================
# PERFORMANCE POR ORIGEM
# =========================================================
st.subheader("📈 Performance e Conversão por Origem")
# =========================================================
# SELETOR DE ORIGEM (KPIs)
# =========================================================
origens_disponiveis = ["TODAS"] + sorted(df_base["ORIGEM"].dropna().unique())

origem = st.selectbox(
    "Origem",
    origens_disponiveis,
    key="origem_performance"
)

df_kpi = df_base if origem == "TODAS" else df_base[df_base["ORIGEM"] == origem]


# =========================================================
# CÁLCULO DOS KPIs
# =========================================================
# =========================================================
# KPI – LEADS CRM (APENAS CRM, FILTRADO SÓ POR DATA E ORIGEM)
# =========================================================

df_crm_kpi = df_crm_f.copy()

if origem != "TODAS":
    df_crm_kpi = df_crm_kpi[df_crm_kpi["ORIGEM"] == origem]

leads = df_crm_kpi["CLIENTE"].nunique()


# KPIs
leads = df_crm_kpi["CLIENTE"].nunique()

analises = df_kpi[df_kpi["STATUS_BASE"] == "ANALISE"]["CLIENTE"].nunique()
aprovados = df_kpi[df_kpi["STATUS_BASE"] == "APROVADO"]["CLIENTE"].nunique()
vendas = df_kpi[df_kpi["STATUS_BASE"] == "VENDA_GERADA"]["CLIENTE"].nunique()



analises = df_kpi[df_kpi["STATUS_BASE"] == "ANALISE"]["CLIENTE"].nunique()
aprovados = df_kpi[df_kpi["STATUS_BASE"] == "APROVADO"]["CLIENTE"].nunique()
vendas = df_kpi[df_kpi["STATUS_BASE"] == "VENDA_GERADA"]["CLIENTE"].nunique()

# Exibindo os KPIs em Cards
c1, c2, c3, c4 = st.columns(4)
c1.metric("Leads CRM (Supremo)", leads)
c2.metric("Análises", analises)
c3.metric("Aprovados", aprovados)
c4.metric("Vendas", vendas)

c5, c6, c7, c8 = st.columns(4)
c5.metric("Lead → Análise", f"{(analises / leads * 100 if leads else 0):.1f}%")
c6.metric("Análise → Aprovação", f"{(aprovados / analises * 100 if analises else 0):.1f}%")
c7.metric("Análise → Venda", f"{(vendas / analises * 100 if analises else 0):.1f}%")
c8.metric("Aprovação → Venda", f"{(vendas / aprovados * 100 if aprovados else 0):.1f}%")

# =========================================================
# STATUS ATUAL
# =========================================================
st.subheader("📌 Status Atual do Funil")

df_atual = df_f.sort_values("DATA").groupby("CLIENTE", as_index=False).last()
kpi = df_atual["STATUS_BASE"].value_counts()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Em Análise", int(kpi.get("ANALISE", 0)))
c2.metric("Reanálise", int(kpi.get("REANALISE", 0)))
c3.metric("Pendência", int(kpi.get("PENDENCIA", 0)))
c4.metric("Reprovado", int(kpi.get("REPROVADO", 0)))

c5, c6, c7, c8 = st.columns(4)
c5.metric("Aprovado", int(kpi.get("APROVADO", 0)))
c6.metric("Aprovado Bacen", int(kpi.get("APROVADO_BACEN", 0)))
c7.metric("Desistiu", int(kpi.get("DESISTIU", 0)))
c8.metric("Leads no Funil", len(df_atual))

leads = df_kpi["CLIENTE"].nunique()
analises = df_kpi[df_kpi["STATUS_BASE"] == "ANALISE"]["CLIENTE"].nunique()
aprovados = df_kpi[df_kpi["STATUS_BASE"] == "APROVADO"]["CLIENTE"].nunique()
vendas = df_kpi[df_kpi["STATUS_BASE"] == "VENDA_GERADA"]["CLIENTE"].nunique()


c1, c2, c3, c4 = st.columns(4)
c1.metric("Leads", leads)
c2.metric("Análises", analises)
c3.metric("Aprovados", aprovados)
c4.metric("Vendas", vendas)

c5, c6, c7, c8 = st.columns(4)
c5.metric("Lead → Análise", f"{(analises/leads*100 if leads else 0):.1f}%")
c6.metric("Análise → Aprovação", f"{(aprovados/analises*100 if analises else 0):.1f}%")
c7.metric("Análise → Venda", f"{(vendas/analises*100 if analises else 0):.1f}%")
c8.metric("Aprovação → Venda", f"{(vendas/aprovados*100 if aprovados else 0):.1f}%")
# =========================================================
# TABELA DE LEADS DA ORIGEM SELECIONADA
# =========================================================
st.subheader("📋 Leads da Origem Selecionada")
# =========================================
# SELETOR DE STATUS (AFETA APENAS A TABELA)
# =========================================
status_tabela_opcoes = ["TODOS"] + sorted(
    df_kpi["STATUS_BASE"].dropna().unique().tolist()
)

status_tabela = st.selectbox(
    "Filtrar leads por status",
    status_tabela_opcoes,
    key="status_tabela_origem"
)

# Só o ÚLTIMO status por cliente (dentro do período + filtros atuais)
df_tabela_origem = (
    df_kpi.sort_values("DATA")
    .groupby("CLIENTE", as_index=False)
    .last()
)

# Filtro de status (após consolidar o último status)
if status_tabela != "TODOS":
    df_tabela_origem = df_tabela_origem[df_tabela_origem["STATUS_BASE"] == status_tabela]

tabela_origem = df_tabela_origem[
    ["CLIENTE", "CORRETOR", "EQUIPE", "ORIGEM", "CAMPANHA", "STATUS_BASE", "DATA"]
].sort_values("DATA", ascending=False)



tabela_origem.rename(
    columns={"DATA": "ULTIMA_ATUALIZACAO"},
    inplace=True
)

st.dataframe(tabela_origem, use_container_width=True)


