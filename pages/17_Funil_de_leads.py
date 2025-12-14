# =========================================================
# FUNIL DE LEADS – ORIGEM, STATUS E CONVERSÃO (REGRAS OFICIAIS)
# =========================================================

import streamlit as st
import pandas as pd
import requests
from datetime import date
from utils.supremo_config import TOKEN_SUPREMO

st.set_page_config(page_title="Funil de Leads", page_icon="📊", layout="wide")

# Logo
try:
    st.image("logo_mr.png", width=120)
except:
    pass

st.title("📊 Funil de Leads – Origem, Status e Conversão")

# =========================================================
# PLANILHA
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

def parse_data(col):
    return pd.to_datetime(col, dayfirst=True, errors="coerce")

def parse_data_base_label(label):
    try:
        mes, ano = label.upper().split()
        return date(int(ano), MESES[mes], 1)
    except:
        return pd.NaT

@st.cache_data(ttl=300)
def carregar_planilha():
    df = pd.read_csv(CSV_URL, dtype=str)
    df.columns = df.columns.str.upper().str.strip()

    df["DATA"] = parse_data(df["DATA"])
    df = df.dropna(subset=["DATA"])

    df["DATA_BASE_LABEL"] = df.get("DATA BASE", "").astype(str)
    df["DATA_BASE_DATE"] = df["DATA_BASE_LABEL"].apply(parse_data_base_label)

    df["CLIENTE"] = df["CLIENTE"].str.upper().str.strip()
    df["CORRETOR"] = df["CORRETOR"].str.upper().str.strip()
    df["EQUIPE"] = df["EQUIPE"].str.upper().str.strip()
    raw = df["SITUAÇÃO"].str.upper().str.strip()

    df["STATUS_BASE"] = ""
    df.loc[raw.str.contains("EM ANÁLISE"), "STATUS_BASE"] = "ANALISE"
    df.loc[raw.str.contains("REANÁLISE"), "STATUS_BASE"] = "REANALISE"
    df.loc[raw.str.contains("APROVADO BACEN"), "STATUS_BASE"] = "APROVADO_BACEN"
    df.loc[(raw.str.contains("APROVADO")) & (~raw.str.contains("BACEN")), "STATUS_BASE"] = "APROVADO"
    df.loc[raw.str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
    df.loc[raw.str.contains("PEND"), "STATUS_BASE"] = "PENDENCIA"
    df.loc[raw.str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA_GERADA"
    df.loc[raw.str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA_INFORMADA"
    df.loc[raw.str.contains("DESIST"), "STATUS_BASE"] = "DESISTIU"

    df = df[df["STATUS_BASE"] != ""]

    # última atualização por cliente
    df = df.sort_values("DATA").groupby("CLIENTE", as_index=False).last()

    return df

@st.cache_data(ttl=1800)
def carregar_crm():
    try:
        r = requests.get(
            "https://api.supremocrm.com.br/v1/leads",
            headers={"Authorization": f"Bearer {TOKEN_SUPREMO}"},
            timeout=20
        )
        if r.status_code != 200:
            raise Exception
        data = r.json().get("data", [])
    except:
        return pd.DataFrame(columns=["CLIENTE", "ORIGEM"])

    df = pd.DataFrame(data)
    if df.empty:
        return pd.DataFrame(columns=["CLIENTE", "ORIGEM"])

    df["CLIENTE"] = df["nome_pessoa"].str.upper().str.strip()
    df["ORIGEM"] = df["nome_origem"].fillna("SEM CADASTRO NO CRM").str.upper()

    return df[["CLIENTE", "ORIGEM"]]

# =========================================================
# CARGA
# =========================================================
df_plan = carregar_planilha()
df_crm = carregar_crm()

df = df_plan.merge(df_crm, on="CLIENTE", how="left")
df["ORIGEM"] = df["ORIGEM"].fillna("SEM CADASTRO NO CRM")

# =========================================================
# PERFORMANCE POR ORIGEM
# =========================================================
st.subheader("📈 Performance e Conversão por Origem")

origem_sel = st.selectbox("Origem", ["TODAS"] + sorted(df["ORIGEM"].unique()))

df_o = df if origem_sel == "TODAS" else df[df["ORIGEM"] == origem_sel]

leads = len(df_o)
analises = (df_o["STATUS_BASE"] == "ANALISE").sum()
reanalises = (df_o["STATUS_BASE"] == "REANALISE").sum()
aprovados = (df_o["STATUS_BASE"] == "APROVADO").sum()
aprovado_bacen = (df_o["STATUS_BASE"] == "APROVADO_BACEN").sum()
reprovados = (df_o["STATUS_BASE"] == "REPROVADO").sum()
vendas = (df_o["STATUS_BASE"] == "VENDA_GERADA").sum()

def pct(a, b):
    return f"{(a / b * 100):.1f}%" if b else "0%"

c1, c2, c3, c4 = st.columns(4)
c1.metric("Leads", leads)
c2.metric("Análises", analises)
c3.metric("Reanálises", reanalises)
c4.metric("Vendas", vendas)

c1.metric("Lead → Análise", pct(analises, leads))
c2.metric("Análise → Aprovação", pct(aprovados, analises))
c3.metric("Análise → Venda", pct(vendas, analises))
c4.metric("Aprovação → Venda", pct(vendas, aprovados))

st.caption(f"Aprovado Bacen: {aprovado_bacen} | Reprovados: {reprovados}")

# =========================================================
# TABELA
# =========================================================
st.subheader("📋 Leads da Origem Selecionada")

st.dataframe(
    df_o[["CLIENTE", "CORRETOR", "EQUIPE", "ORIGEM", "STATUS_BASE", "DATA"]]
    .rename(columns={"DATA": "ULTIMA_ATUALIZACAO"})
    .sort_values("ULTIMA_ATUALIZACAO", ascending=False),
    use_container_width=True
)
