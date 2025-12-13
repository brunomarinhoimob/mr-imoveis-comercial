# =========================================================
# FUNIL DE LEADS – ORIGEM, STATUS, CONVERSÃO E AUDITORIA
# =========================================================

import streamlit as st
import pandas as pd
import requests
from datetime import datetime

from utils.supremo_config import TOKEN_SUPREMO

# =========================================================
# CONFIG PÁGINA
# =========================================================
st.set_page_config(
    page_title="Funil de Leads",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Funil de Leads – Origem, Status e Conversão")

# =========================================================
# GOOGLE SHEETS
# =========================================================
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

# =========================================================
# FUNÇÕES AUX
# =========================================================
def limpar_data(col):
    return pd.to_datetime(col, dayfirst=True, errors="coerce").dt.date

def mes_ano_para_date(v):
    meses = {
        "JANEIRO":1,"FEVEREIRO":2,"MARÇO":3,"MARCO":3,"ABRIL":4,"MAIO":5,
        "JUNHO":6,"JULHO":7,"AGOSTO":8,"SETEMBRO":9,"OUTUBRO":10,
        "NOVEMBRO":11,"DEZEMBRO":12
    }
    try:
        p = str(v).upper().split()
        return datetime(int(p[-1]), meses[p[0]], 1).date()
    except:
        return pd.NaT

# =========================================================
# PLANILHA COMPLETA (linha do tempo)
# =========================================================
@st.cache_data(ttl=300)
def carregar_planilha_completa():
    df = pd.read_csv(CSV_URL)
    df.columns = [c.strip().upper() for c in df.columns]

    df["DIA"] = limpar_data(df["DATA"])
    df["DATA_BASE_LABEL"] = df["DATA BASE"].astype(str)
    df["DATA_BASE"] = df["DATA BASE"].apply(mes_ano_para_date)

    df["STATUS_RAW"] = df["SITUAÇÃO"].astype(str).str.upper()
    df["NOME_CLIENTE"] = df["CLIENTE"].astype(str).str.upper().str.strip()
    df["CHAVE"] = df["NOME_CLIENTE"]

    df["CORRETOR"] = df["CORRETOR"].astype(str).str.upper()
    df["EQUIPE"] = df["EQUIPE"].astype(str).str.upper()

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

    return df

df_full = carregar_planilha_completa()

# =========================================================
# PLANILHA FINAL (último status)
# =========================================================
df = (
    df_full
    .sort_values("DIA")
    .groupby("CHAVE")
    .tail(1)
)

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

    dfc = pd.DataFrame(dados)
    dfc["CHAVE"] = dfc.get("nome_pessoa","").astype(str).str.upper().str.strip()
    dfc["ORIGEM"] = dfc.get("nome_origem","SEM ORIGEM").fillna("SEM ORIGEM")
    return dfc[["CHAVE","ORIGEM"]]

df_crm = carregar_crm()

df = df.merge(df_crm, on="CHAVE", how="left")
df["ORIGEM"] = df["ORIGEM"].fillna("SEM CADASTRO NO CRM")

# =========================================================
# FILTROS
# =========================================================
st.sidebar.header("Filtros")

modo = st.sidebar.radio("Modo de período", ["DIA","DATA BASE"])

if modo == "DIA":
    ini, fim = st.sidebar.date_input(
        "Período",
        value=(df["DIA"].min(), df["DIA"].max())
    )
    df = df[(df["DIA"] >= ini) & (df["DIA"] <= fim)]
    df_full_filtro = df_full[(df_full["DIA"] >= ini) & (df_full["DIA"] <= fim)]
else:
    bases = st.sidebar.multiselect(
        "Data Base",
        sorted(df["DATA_BASE_LABEL"].unique()),
        default=df["DATA_BASE_LABEL"].unique()
    )
    df = df[df["DATA_BASE_LABEL"].isin(bases)]
    df_full_filtro = df_full[df_full["DATA_BASE_LABEL"].isin(bases)]

# =========================================================
# 🔝 CARDS MACRO
# =========================================================
st.subheader("📊 Visão Macro do Funil")

status = df["STATUS_BASE"].value_counts()
df_vendas_validas = df[~df["STATUS_BASE"].isin(["DESISTIU"])]

c1,c2,c3,c4 = st.columns(4)
c1.metric("Leads no Funil", len(df))
c2.metric("Análises", status.get("ANALISE",0))
c3.metric("Reanálises", status.get("REANALISE",0))
c4.metric("Pendências", status.get("PENDENCIA",0))

c5,c6,c7,c8 = st.columns(4)
c5.metric("Aprovados", status.get("APROVADO",0))
c6.metric("Aprovados Bacen", status.get("APROVADO_BACEN",0))
c7.metric("Reprovados", status.get("REPROVADO",0))
c8.metric("Desistidos", status.get("DESISTIU",0))

c9,c10 = st.columns(2)
c9.metric("Vendas Informadas", (df_vendas_validas["STATUS_BASE"]=="VENDA_INFORMADA").sum())
c10.metric("Vendas Geradas", (df_vendas_validas["STATUS_BASE"]=="VENDA_GERADA").sum())

# =========================================================
# PERFORMANCE POR ORIGEM + CONVERSÃO
# =========================================================
st.subheader("📌 Performance por Origem")

origens = ["TODAS"] + sorted(df["ORIGEM"].unique())
origem_sel = st.selectbox("Selecione a origem", origens)

df_origem = df if origem_sel=="TODAS" else df[df["ORIGEM"]==origem_sel]

tipo_venda = st.radio(
    "Tipo de venda para conversão",
    ["Venda Gerada + Informada","Somente Venda Gerada"],
    horizontal=True
)

vendas_validas = ["VENDA_GERADA","VENDA_INFORMADA"] if tipo_venda=="Venda Gerada + Informada" else ["VENDA_GERADA"]

total = len(df_origem)
analises = (df_origem["STATUS_BASE"]=="ANALISE").sum()
aprovados = df_origem["STATUS_BASE"].isin(["APROVADO","APROVADO_BACEN"]).sum()
vendas = df_origem["STATUS_BASE"].isin(vendas_validas).sum()

tx1 = analises/total*100 if total else 0
tx2 = aprovados/analises*100 if analises else 0
tx3 = vendas/analises*100 if analises else 0
tx4 = vendas/aprovados*100 if aprovados else 0

c1,c2,c3,c4 = st.columns(4)
c1.metric("Lead → Análise", f"{tx1:.1f}%")
c2.metric("Análise → Aprovação", f"{tx2:.1f}%")
c3.metric("Análise → Venda", f"{tx3:.1f}%")
c4.metric("Aprovação → Venda", f"{tx4:.1f}%")

# =========================================================
# 🔎 BUSCA DE CLIENTE
# =========================================================
st.subheader("🔎 Auditoria de Cliente")

busca = st.text_input("Digite o nome do cliente")

if busca:
    cli = df_full_filtro[
        df_full_filtro["NOME_CLIENTE"].str.contains(busca.upper(), na=False)
    ]

    if not cli.empty:
        ultimo = cli.sort_values("DIA").iloc[-1]

        c1,c2,c3 = st.columns(3)
        c1.metric("Corretor", ultimo["CORRETOR"])
        c2.metric("Situação Atual", ultimo["STATUS_BASE"])
        c3.metric("Origem CRM", ultimo["ORIGEM"])

        st.subheader("📜 Linha do Tempo")
        st.dataframe(
            cli.sort_values("DIA"),
            use_container_width=True
        )
    else:
        st.warning("Cliente não encontrado no período.")
