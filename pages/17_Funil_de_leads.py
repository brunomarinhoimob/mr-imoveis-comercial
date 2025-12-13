# =========================================================
# FUNIL DE LEADS – ORIGEM, STATUS E CONVERSÃO (REGRA CORRETA)
# =========================================================

import streamlit as st
import pandas as pd
import requests
from datetime import datetime

from utils.supremo_config import TOKEN_SUPREMO

st.set_page_config(
    page_title="Funil de Leads",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Funil de Leads – Origem, Status e Conversão")

# =========================================================
# PLANILHA (BASE ORIGINAL)
# =========================================================
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

# =========================================================
# FUNÇÕES
# =========================================================
def parse_data(col):
    return pd.to_datetime(col, dayfirst=True, errors="coerce")

@st.cache_data(ttl=300)
def carregar_planilha():
    df = pd.read_csv(CSV_URL, dtype=str)
    df.columns = df.columns.str.upper().str.strip()

    df["DATA"] = parse_data(df["DATA"])
    df = df.dropna(subset=["DATA"])

    df["CLIENTE"] = df["CLIENTE"].str.upper().str.strip()
    df["CORRETOR"] = df["CORRETOR"].str.upper().str.strip()
    df["EQUIPE"] = df["EQUIPE"].str.upper().str.strip()
    df["STATUS_RAW"] = df["SITUAÇÃO"].str.upper().str.strip()

    df["STATUS_BASE"] = ""
    df.loc[df["STATUS_RAW"].str.contains("EM ANÁLISE"), "STATUS_BASE"] = "ANALISE"
    df.loc[df["STATUS_RAW"].str.contains("REANÁLISE"), "STATUS_BASE"] = "REANALISE"
    df.loc[df["STATUS_RAW"].str.contains("APROVADO BACEN"), "STATUS_BASE"] = "APROVADO_BACEN"
    df.loc[df["STATUS_RAW"].str.contains("APROVA"), "STATUS_BASE"] = "APROVADO"
    df.loc[df["STATUS_RAW"].str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
    df.loc[df["STATUS_RAW"].str.contains("PEND"), "STATUS_BASE"] = "PENDENCIA"
    df.loc[df["STATUS_RAW"].str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA_GERADA"
    df.loc[df["STATUS_RAW"].str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA_INFORMADA"
    df.loc[df["STATUS_RAW"].str.contains("DESIST"), "STATUS_BASE"] = "DESISTIU"

    # Último status por cliente
    df = df.sort_values("DATA")
    df = df.groupby("CLIENTE", as_index=False).last()

    return df

# =========================================================
# CRM – ORIGEM
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

    df = pd.DataFrame(dados)
    df["CLIENTE"] = df["nome_pessoa"].astype(str).str.upper().str.strip()
    df["ORIGEM"] = df.get("nome_origem", "SEM CADASTRO NO CRM").fillna("SEM CADASTRO NO CRM")
    return df[["CLIENTE", "ORIGEM"]]

# =========================================================
# CARGA
# =========================================================
df_plan = carregar_planilha()
df_crm = carregar_crm()

df = df_plan.merge(df_crm, on="CLIENTE", how="left")
df["ORIGEM"] = df["ORIGEM"].fillna("SEM CADASTRO NO CRM")

# =========================================================
# FILTRO POR ORIGEM
# =========================================================
st.subheader("📈 Performance e Conversão por Origem")

origens = ["TODAS"] + sorted(df["ORIGEM"].unique())
origem_sel = st.selectbox("Origem", origens)

df_o = df if origem_sel == "TODAS" else df[df["ORIGEM"] == origem_sel]

# =========================================================
# KPIs (REGRA CORRETA)
# =========================================================
leads = len(df_o)

analises = df_o[df_o["STATUS_BASE"].isin(["ANALISE", "REANALISE", "APROVADO", "APROVADO_BACEN", "VENDA_GERADA", "VENDA_INFORMADA"])].shape[0]

aprovados = df_o[df_o["STATUS_BASE"].isin(["APROVADO", "APROVADO_BACEN", "VENDA_GERADA", "VENDA_INFORMADA"])].shape[0]

vendas = df_o[
    df_o["STATUS_BASE"].isin(["VENDA_GERADA", "VENDA_INFORMADA"])
    & ~df_o["STATUS_BASE"].isin(["DESISTIU"])
].shape[0]

# =========================================================
# CARDS
# =========================================================
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
# TABELA DE LEADS DA ORIGEM
# =========================================================
st.divider()
st.subheader("📋 Leads da Origem Selecionada")

st.dataframe(
    df_o[[
        "CLIENTE",
        "CORRETOR",
        "EQUIPE",
        "STATUS_BASE",
        "DATA"
    ]].sort_values("DATA", ascending=False),
    use_container_width=True
)
