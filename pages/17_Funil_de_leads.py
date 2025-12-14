import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, date

st.set_page_config(layout="wide")

# ===============================
# CONFIG
# ===============================
TOKEN = "SEU_TOKEN_AQUI"
CRM_URL = "https://api.supremocrm.com.br/v1/leads"
SHEET_URL = "https://docs.google.com/spreadsheets/d/SEU_SHEET_ID/export?format=csv&gid=SEU_GID"

# ===============================
# FUNÇÕES
# ===============================
@st.cache_data
def carregar_planilha():
    df = pd.read_csv(SHEET_URL, dtype=str)
    df.columns = df.columns.str.upper().str.strip()
    df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce")
    df["CLIENTE"] = df["CLIENTE"].str.upper().str.strip()
    return df


@st.cache_data
def carregar_crm():
    headers = {"Authorization": f"Bearer {TOKEN}"}
    page = 1
    dados = []

    while True:
        resp = requests.get(
            CRM_URL,
            headers=headers,
            params={"page": page, "per_page": 1000},
            timeout=30
        )
        if resp.status_code != 200:
            break

        js = resp.json().get("dados", [])
        if not js:
            break

        dados.extend(js)
        page += 1

    df = pd.json_normalize(dados)
    df["CLIENTE"] = df["nome_pessoa"].str.upper().str.strip()
    return df[["CLIENTE", "nome_origem", "nome_campanha"]]


def status_base(txt):
    if pd.isna(txt):
        return "OUTRO"
    t = txt.upper()
    if "DESIST" in t:
        return "DESISTIU"
    if "VENDA INFORMADA" in t:
        return "VENDA_INFORMADA"
    if "VENDA" in t:
        return "VENDA_GERADA"
    if "REANÁLISE" in t or "REANALISE" in t:
        return "REANALISE"
    if "APROVADO BACEN" in t:
        return "APROVADO_BACEN"
    if "APROVA" in t:
        return "APROVADO"
    if "REPROV" in t:
        return "REPROVADO"
    if "PEND" in t:
        return "PENDENCIA"
    if "ANÁLISE" in t or "ANALISE" in t:
        return "EM_ANALISE"
    return "OUTRO"


# ===============================
# CARGA DE DADOS
# ===============================
df = carregar_planilha()
df["STATUS_BASE"] = df["SITUAÇÃO"].apply(status_base)

df_crm = carregar_crm()
df = df.merge(df_crm, on="CLIENTE", how="left")

# ===============================
# DATA BASE
# ===============================
df["DATA_BASE_LABEL"] = df["DATA BASE"]

meses = {
    "JANEIRO": 1, "FEVEREIRO": 2, "MARÇO": 3, "ABRIL": 4,
    "MAIO": 5, "JUNHO": 6, "JULHO": 7, "AGOSTO": 8,
    "SETEMBRO": 9, "OUTUBRO": 10, "NOVEMBRO": 11, "DEZEMBRO": 12
}

def parse_data_base(x):
    try:
        mes, ano = x.split()
        return date(int(ano), meses[mes.upper()], 1)
    except:
        return None

df["DATA_BASE_DATE"] = df["DATA_BASE_LABEL"].apply(parse_data_base)

# ===============================
# SIDEBAR
# ===============================
st.sidebar.title("Filtros")

modo = st.sidebar.radio("Filtro de período", ["DIA", "DATA BASE"])

if modo == "DIA":
    ini, fim = st.sidebar.date_input(
        "Período",
        value=(df["DATA"].min().date(), df["DATA"].max().date())
    )
    df = df[(df["DATA"].dt.date >= ini) & (df["DATA"].dt.date <= fim)]
else:
    bases = st.sidebar.multiselect(
        "Data Base",
        sorted(df["DATA_BASE_LABEL"].dropna().unique())
    )
    if bases:
        df = df[df["DATA_BASE_LABEL"].isin(bases)]

origem = st.sidebar.selectbox(
    "Origem",
    ["Todas"] + sorted(df["nome_origem"].dropna().unique())
)

if origem != "Todas":
    df = df[df["nome_origem"] == origem]

# ===============================
# HISTÓRICO POR CLIENTE
# ===============================
historico = df.sort_values("DATA")

clientes = historico["CLIENTE"].unique()

def teve_status(cliente, status):
    return any(historico[(historico["CLIENTE"] == cliente)]["STATUS_BASE"] == status)

leads = len(clientes)

analises = sum(teve_status(c, "EM_ANALISE") for c in clientes)
aprovados = sum(teve_status(c, "APROVADO") for c in clientes)

vendas = 0
for c in clientes:
    teve_venda = teve_status(c, "VENDA_GERADA") or teve_status(c, "VENDA_INFORMADA")
    desistiu = teve_status(c, "DESISTIU")
    if teve_venda and not desistiu:
        vendas += 1

# ===============================
# CARDS
# ===============================
col1, col2, col3, col4 = st.columns(4)

col1.metric("Leads", leads)
col2.metric("Análises", analises)
col3.metric("Aprovados", aprovados)
col4.metric("Vendas", vendas)

# ===============================
# CONVERSÕES
# ===============================
st.subheader("Conversões")

c1, c2, c3 = st.columns(3)

c1.metric(
    "Lead → Análise",
    f"{(analises / leads * 100):.1f}%" if leads else "0%"
)
c2.metric(
    "Análise → Aprovação",
    f"{(aprovados / analises * 100):.1f}%" if analises else "0%"
)
c3.metric(
    "Aprovação → Venda",
    f"{(vendas / aprovados * 100):.1f}%" if aprovados else "0%"
)

# ===============================
# TABELA FINAL
# ===============================
st.subheader("Leads no período")
st.dataframe(
    df.sort_values("DATA", ascending=False),
    use_container_width=True
)
