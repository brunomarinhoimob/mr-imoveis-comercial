# =========================================================
# FUNIL DE LEADS – ORIGEM, STATUS E CONVERSÃO (OFICIAL)
# =========================================================

import streamlit as st
import pandas as pd
import requests
from datetime import date
from utils.supremo_config import TOKEN_SUPREMO

st.set_page_config(page_title="Funil de Leads", page_icon="🎯", layout="wide")
st.title("🎯 Funil de Leads – Origem, Status e Conversão")

# =========================================================
# PLANILHA (LINK OFICIAL – NÃO ALTERAR)
# =========================================================
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

MESES = {
    "JANEIRO": 1, "FEVEREIRO": 2, "MARÇO": 3, "MARCO": 3,
    "ABRIL": 4, "MAIO": 5, "JUNHO": 6, "JULHO": 7,
    "AGOSTO": 8, "SETEMBRO": 9, "OUTUBRO": 10,
    "NOVEMBRO": 11, "DEZEMBRO": 12,
}

def parse_data_base(label):
    try:
        mes, ano = label.upper().split()
        return date(int(ano), MESES.get(mes, 1), 1)
    except:
        return pd.NaT

# =========================================================
# LOAD PLANILHA
# =========================================================
@st.cache_data(ttl=300)
def carregar_planilha():
    df = pd.read_csv(CSV_URL, dtype=str)
    df.columns = df.columns.str.upper().str.strip()

    df["DATA"] = pd.to_datetime(df["DATA"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["DATA"])

    df["DATA_BASE_LABEL"] = df.get("DATA BASE", "")
    df["DATA_BASE_DATE"] = df["DATA_BASE_LABEL"].apply(parse_data_base)

    for col in ["CLIENTE", "CORRETOR", "EQUIPE", "SITUAÇÃO"]:
        df[col] = df[col].astype(str).str.upper().str.strip()

    df["STATUS_BASE"] = ""
    mapa = {
        "EM ANÁLISE": "ANALISE",
        "REANÁLISE": "REANALISE",
        "APROVADO BACEN": "APROVADO_BACEN",
        "APROV": "APROVADO",
        "REPROV": "REPROVADO",
        "PEND": "PENDENCIA",
        "VENDA GERADA": "VENDA_GERADA",
        "VENDA INFORMADA": "VENDA_INFORMADA",
        "DESIST": "DESISTIU",
    }

    for k, v in mapa.items():
        df.loc[df["SITUAÇÃO"].str.contains(k), "STATUS_BASE"] = v

    df = df[df["STATUS_BASE"] != ""]

    # Última movimentação do cliente
    df = df.sort_values("DATA").groupby("CLIENTE", as_index=False).last()
    return df

# =========================================================
# CRM – ÚLTIMOS 1000 LEADS
# =========================================================
@st.cache_data(ttl=1800)
def carregar_crm():
    url = "https://api.supremocrm.com.br/v1/leads"
    headers = {"Authorization": f"Bearer {TOKEN_SUPREMO}"}
    dados, pagina = [], 1

    while len(dados) < 1000:
        r = requests.get(url, headers=headers, params={"pagina": pagina})
        if r.status_code != 200 or not r.json().get("data"):
            break
        dados.extend(r.json()["data"])
        pagina += 1

    df = pd.DataFrame(dados)
    if df.empty:
        return pd.DataFrame(columns=["CLIENTE", "ORIGEM"])

    df["CLIENTE"] = df["nome_pessoa"].astype(str).str.upper().str.strip()
    df["ORIGEM"] = df.get("nome_origem", "SEM CADASTRO NO CRM").fillna("SEM CADASTRO NO CRM")
    df["ORIGEM"] = df["ORIGEM"].astype(str).str.upper().str.strip()
    return df[["CLIENTE", "ORIGEM"]]

# =========================================================
# CARGA GERAL
# =========================================================
df = carregar_planilha().merge(carregar_crm(), on="CLIENTE", how="left")
df["ORIGEM"] = df["ORIGEM"].fillna("SEM CADASTRO NO CRM")

# =========================================================
# FILTROS
# =========================================================
st.sidebar.header("Filtros")

modo = st.sidebar.radio("Tipo de Período", ["DIA", "DATA BASE"])

df_f = df.copy()

if modo == "DIA":
    ini, fim = st.sidebar.date_input(
        "Período",
        (df_f["DATA"].min().date(), df_f["DATA"].max().date())
    )
    df_f = df_f[(df_f["DATA"].dt.date >= ini) & (df_f["DATA"].dt.date <= fim)]
else:
    bases = sorted(df_f["DATA_BASE_LABEL"].dropna().unique())
    bases_sel = st.sidebar.multiselect("Data Base", bases, default=bases)
    if bases_sel:
        df_f = df_f[df_f["DATA_BASE_LABEL"].isin(bases_sel)]

equipes = ["TODAS"] + sorted(df_f["EQUIPE"].unique())
eq = st.sidebar.selectbox("Equipe", equipes)
if eq != "TODAS":
    df_f = df_f[df_f["EQUIPE"] == eq]

corretores = ["TODOS"] + sorted(df_f["CORRETOR"].unique())
cor = st.sidebar.selectbox("Corretor", corretores)
if cor != "TODOS":
    df_f = df_f[df_f["CORRETOR"] == cor]

# =========================================================
# STATUS ATUAL DO FUNIL
# =========================================================
st.subheader("📌 Status Atual do Funil")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Em Análise", (df_f["STATUS_BASE"] == "ANALISE").sum())
c2.metric("Reanálises", (df_f["STATUS_BASE"] == "REANALISE").sum())
c3.metric("Pendências", (df_f["STATUS_BASE"] == "PENDENCIA").sum())
c4.metric("Reprovados", (df_f["STATUS_BASE"] == "REPROVADO").sum())

# =========================================================
# PERFORMANCE E CONVERSÃO POR ORIGEM
# =========================================================
st.subheader("📈 Performance e Conversão por Origem")

origem = st.selectbox("Origem", ["TODAS"] + sorted(df_f["ORIGEM"].unique()))
df_o = df_f if origem == "TODAS" else df_f[df_f["ORIGEM"] == origem]

tipo_venda = st.radio(
    "Tipo de Venda para Conversão",
    ["Vendas Geradas + Informadas", "Apenas Vendas Geradas"]
)

leads = len(df_o)
analises = (df_o["STATUS_BASE"] == "ANALISE").sum()
reanalises = (df_o["STATUS_BASE"] == "REANALISE").sum()
aprovados = df_o["STATUS_BASE"].isin(
    ["APROVADO", "APROVADO_BACEN", "VENDA_GERADA", "VENDA_INFORMADA"]
).sum()

if tipo_venda == "Apenas Vendas Geradas":
    vendas = (df_o["STATUS_BASE"] == "VENDA_GERADA").sum()
else:
    vendas = df_o["STATUS_BASE"].isin(["VENDA_GERADA", "VENDA_INFORMADA"]).sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Leads", leads)
c2.metric("Análises", analises)
c3.metric("Reanálises", reanalises)
c4.metric("Vendas", vendas)

# =========================================================
# TABELA – ÚLTIMA ATUALIZAÇÃO DO LEAD
# =========================================================
st.subheader("📋 Leads da Origem Selecionada")

st.dataframe(
    df_o.sort_values("DATA", ascending=False)[
        ["CLIENTE", "CORRETOR", "EQUIPE", "STATUS_BASE", "DATA"]
    ].rename(columns={"DATA": "ULTIMA_ATUALIZACAO"}),
    use_container_width=True
)
