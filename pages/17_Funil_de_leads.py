# =========================================================
# FUNIL DE LEADS – ORIGEM, STATUS E CONVERSÃO
# =========================================================

import streamlit as st
import pandas as pd
import requests
from datetime import date
from utils.supremo_config import TOKEN_SUPREMO

# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================
st.set_page_config(
    page_title="Funil de Leads",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Funil de Leads – Origem, Status e Conversão")

# =========================================================
# FONTE DA PLANILHA
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
    if not label or pd.isna(label):
        return pd.NaT
    partes = str(label).upper().split()
    if len(partes) < 2:
        return pd.NaT
    mes = MESES.get(partes[0])
    try:
        ano = int(partes[-1])
    except:
        return pd.NaT
    if not mes:
        return pd.NaT
    return date(ano, mes, 1)

# =========================================================
# CARGA DA PLANILHA
# =========================================================
@st.cache_data(ttl=300)
def carregar_planilha():
    df = pd.read_csv(CSV_URL, dtype=str)
    df.columns = df.columns.str.upper().str.strip()

    df["DATA"] = parse_data(df["DATA"])
    df = df.dropna(subset=["DATA"])

    df["DATA_BASE_LABEL"] = df.get("DATA BASE", "").astype(str).str.strip()
    df["DATA_BASE_DATE"] = df["DATA_BASE_LABEL"].apply(parse_data_base)

    for col in ["CLIENTE", "CORRETOR", "EQUIPE"]:
        df[col] = df[col].astype(str).str.upper().str.strip()

    df["STATUS_RAW"] = df["SITUAÇÃO"].astype(str).str.upper().str.strip()
    df["STATUS_BASE"] = ""

    regras = {
        "EM ANÁLISE": "ANALISE",
        "REANÁLISE": "REANALISE",
        "APROVADO BACEN": "APROVADO_BACEN",
        "APROVA": "APROVADO",
        "REPROV": "REPROVADO",
        "PEND": "PENDENCIA",
        "VENDA GERADA": "VENDA_GERADA",
        "VENDA INFORMADA": "VENDA_INFORMADA",
        "DESIST": "DESISTIU",
    }

    for chave, valor in regras.items():
        df.loc[df["STATUS_RAW"].str.contains(chave), "STATUS_BASE"] = valor

    df = df[df["STATUS_BASE"] != ""]

    # Último status por cliente (lead permanece no funil)
    df = df.sort_values("DATA")
    df = df.groupby("CLIENTE", as_index=False).last()

    return df

# =========================================================
# CARGA DO CRM
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
        return pd.DataFrame(columns=["CLIENTE", "ORIGEM", "CAMPANHA"])

    df = pd.DataFrame(dados)
    df["CLIENTE"] = df["nome_pessoa"].astype(str).str.upper().str.strip()
    df["ORIGEM"] = df.get("nome_origem", "SEM CADASTRO NO CRM").fillna("SEM CADASTRO NO CRM")
    df["CAMPANHA"] = df.get("nome_campanha", "-").fillna("-")

    df["ORIGEM"] = df["ORIGEM"].astype(str).str.upper().str.strip()
    df["CAMPANHA"] = df["CAMPANHA"].astype(str).str.upper().str.strip()

    return df[["CLIENTE", "ORIGEM", "CAMPANHA"]]

# =========================================================
# CARGA GERAL
# =========================================================
df_plan = carregar_planilha()
df_crm = carregar_crm()

df = df_plan.merge(df_crm, on="CLIENTE", how="left")
df["ORIGEM"] = df["ORIGEM"].fillna("SEM CADASTRO NO CRM")
df["CAMPANHA"] = df["CAMPANHA"].fillna("-")

# =========================================================
# FILTROS
# =========================================================
st.sidebar.header("Filtros")

modo_periodo = st.sidebar.radio("Modo de período", ["DIA", "DATA BASE"])
df_filtro = df.copy()

if modo_periodo == "DIA":
    ini, fim = st.sidebar.date_input(
        "Período",
        value=(df_filtro["DATA"].min().date(), df_filtro["DATA"].max().date())
    )
    df_filtro = df_filtro[
        (df_filtro["DATA"].dt.date >= ini) &
        (df_filtro["DATA"].dt.date <= fim)
    ]
else:
    bases = sorted(
        df_filtro["DATA_BASE_LABEL"].dropna().unique(),
        key=lambda x: parse_data_base(x) or date(1900, 1, 1)
    )
    sel = st.sidebar.multiselect("Data Base", bases, default=bases)
    if sel:
        df_filtro = df_filtro[df_filtro["DATA_BASE_LABEL"].isin(sel)]

equipe = st.sidebar.selectbox("Equipe", ["TODAS"] + sorted(df_filtro["EQUIPE"].unique()))
if equipe != "TODAS":
    df_filtro = df_filtro[df_filtro["EQUIPE"] == equipe]

corretor = st.sidebar.selectbox("Corretor", ["TODOS"] + sorted(df_filtro["CORRETOR"].unique()))
if corretor != "TODOS":
    df_filtro = df_filtro[df_filtro["CORRETOR"] == corretor]

# =========================================================
# STATUS ATUAL
# =========================================================
st.subheader("📌 Status Atual do Funil")

kpi = df_filtro["STATUS_BASE"].value_counts()

cols = st.columns(4)
cols[0].metric("Em Análise", int(kpi.get("ANALISE", 0)))
cols[1].metric("Reanálise", int(kpi.get("REANALISE", 0)))
cols[2].metric("Pendência", int(kpi.get("PENDENCIA", 0)))
cols[3].metric("Reprovado", int(kpi.get("REPROVADO", 0)))

cols = st.columns(4)
cols[0].metric("Aprovado", int(kpi.get("APROVADO", 0)))
cols[1].metric("Aprovado Bacen", int(kpi.get("APROVADO_BACEN", 0)))
cols[2].metric("Desistiu", int(kpi.get("DESISTIU", 0)))
cols[3].metric("Leads no Funil", len(df_filtro))

# =========================================================
# PERFORMANCE POR ORIGEM
# =========================================================
st.subheader("📈 Performance e Conversão por Origem")

origem = st.selectbox("Origem", ["TODAS"] + sorted(df_filtro["ORIGEM"].unique()))
df_o = df_filtro if origem == "TODAS" else df_filtro[df_filtro["ORIGEM"] == origem]

leads = len(df_o)
analises = df_o[df_o["STATUS_BASE"] != ""].shape[0]
aprovados = df_o[df_o["STATUS_BASE"].isin(["APROVADO", "APROVADO_BACEN", "VENDA_GERADA", "VENDA_INFORMADA"])].shape[0]
vendas = df_o[df_o["STATUS_BASE"].isin(["VENDA_GERADA", "VENDA_INFORMADA"])].shape[0]

cols = st.columns(4)
cols[0].metric("Leads", leads)
cols[1].metric("Análises", analises)
cols[2].metric("Aprovados", aprovados)
cols[3].metric("Vendas", vendas)

cols = st.columns(4)
cols[0].metric("Lead → Análise", f"{(analises/leads*100 if leads else 0):.1f}%")
cols[1].metric("Análise → Aprovação", f"{(aprovados/analises*100 if analises else 0):.1f}%")
cols[2].metric("Análise → Venda", f"{(vendas/analises*100 if analises else 0):.1f}%")
cols[3].metric("Aprovação → Venda", f"{(vendas/aprovados*100 if aprovados else 0):.1f}%")

# =========================================================
# TABELA
# =========================================================
st.divider()
st.subheader("📋 Leads")

tabela = df_o[["CLIENTE", "CORRETOR", "EQUIPE", "STATUS_BASE", "DATA"]]
tabela = tabela.sort_values("DATA", ascending=False)
tabela.rename(columns={"DATA": "ULTIMA_ATUALIZACAO"}, inplace=True)

st.dataframe(tabela, use_container_width=True)
