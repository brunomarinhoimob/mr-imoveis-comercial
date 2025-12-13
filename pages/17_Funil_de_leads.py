# =========================================================
# FUNIL DE LEADS – ORIGEM, STATUS E CONVERSÃO (OFICIAL)
# BASEADO NA 99_PAGINA_TESTE (SEM INVENTAR)
# =========================================================

import streamlit as st
import pandas as pd
import requests
from datetime import datetime

from utils.supremo_config import TOKEN_SUPREMO

# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================
st.set_page_config(
    page_title="Funil de Leads • Origem & Conversão",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Funil de Leads – Origem, Status e Conversão")

# =========================================================
# GOOGLE SHEETS (MESMO DA 99)
# =========================================================
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID_ANALISES = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ANALISES}"

# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================
def limpar_data(col):
    return pd.to_datetime(col, dayfirst=True, errors="coerce").dt.date

def mes_ano_para_date(valor):
    meses = {
        "JANEIRO": 1, "FEVEREIRO": 2, "MARÇO": 3, "MARCO": 3,
        "ABRIL": 4, "MAIO": 5, "JUNHO": 6, "JULHO": 7,
        "AGOSTO": 8, "SETEMBRO": 9, "OUTUBRO": 10,
        "NOVEMBRO": 11, "DEZEMBRO": 12,
    }
    try:
        p = str(valor).upper().split()
        return datetime(int(p[-1]), meses[p[0]], 1).date()
    except:
        return pd.NaT

# =========================================================
# PLANILHA – FUNIL (IGUAL À 99, COM AJUSTES)
# =========================================================
@st.cache_data(ttl=300)
def carregar_planilha():
    df = pd.read_csv(CSV_URL)
    df.columns = [c.strip().upper() for c in df.columns]

    df["DIA"] = limpar_data(df["DATA"])
    df["DATA_BASE"] = df["DATA BASE"].apply(mes_ano_para_date)
    df["DATA_BASE_LABEL"] = df["DATA BASE"].astype(str)

    df["STATUS_RAW"] = df["SITUAÇÃO"].astype(str).str.upper()

    df = df[df["STATUS_RAW"].str.contains(
        "ANÁLISE|REANÁLISE|APROV|REPROV|VENDA|DESIST|PEND",
        regex=True
    )]

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

    # Último status do cliente
    df = df.sort_values("DIA")
    df = df.groupby("CHAVE").tail(1)

    return df

df_plan = carregar_planilha()

# =========================================================
# SIDEBAR – FILTROS (IGUAL À 99)
# =========================================================
st.sidebar.header("Filtros")

modo = st.sidebar.radio("Modo de período", ["DIA", "DATA BASE"])

if modo == "DIA":
    ini, fim = st.sidebar.date_input(
        "Período",
        value=(df_plan["DIA"].min(), df_plan["DIA"].max())
    )
    df_plan = df_plan[(df_plan["DIA"] >= ini) & (df_plan["DIA"] <= fim)]
else:
    bases = st.sidebar.multiselect(
        "Data Base",
        sorted(df_plan["DATA_BASE_LABEL"].unique()),
        default=df_plan["DATA_BASE_LABEL"].unique()
    )
    df_plan = df_plan[df_plan["DATA_BASE_LABEL"].isin(bases)]

equipes = sorted(df_plan["EQUIPE"].unique())
equipe_sel = st.sidebar.selectbox("Equipe", ["TODAS"] + equipes)
if equipe_sel != "TODAS":
    df_plan = df_plan[df_plan["EQUIPE"] == equipe_sel]

corretores = sorted(df_plan["CORRETOR"].unique())
corretor_sel = st.sidebar.selectbox("Corretor", ["TODOS"] + corretores)
if corretor_sel != "TODOS":
    df_plan = df_plan[df_plan["CORRETOR"] == corretor_sel]

# =========================================================
# CRM – ÚLTIMOS 1000 LEADS
# =========================================================
@st.cache_data(ttl=1800)
def carregar_crm_ultimos_1000():
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

    df["CHAVE"] = df["nome_pessoa"].astype(str).str.upper().str.strip()
    df["ORIGEM"] = df.get("nome_origem", "SEM ORIGEM").fillna("SEM ORIGEM")
    df["CAMPANHA"] = df.get("nome_campanha", "-").fillna("-")

    return df

df_crm = carregar_crm_ultimos_1000()

# =========================================================
# CRUZAMENTO
# =========================================================
df = df_plan.merge(
    df_crm[["CHAVE", "ORIGEM", "CAMPANHA"]],
    on="CHAVE",
    how="left"
)

df["ORIGEM"] = df["ORIGEM"].fillna("SEM CADASTRO NO CRM")

# =========================================================
# STATUS ATUAL – CARDS MACRO
# =========================================================
st.subheader("📌 Status Atual do Funil")

kpi = df["STATUS_BASE"].value_counts()
df_vendas_validas = df[~df["STATUS_BASE"].isin(["DESISTIU"])]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Em Análise", kpi.get("ANALISE", 0))
c2.metric("Reanálise", kpi.get("REANALISE", 0))
c3.metric("Pendência", kpi.get("PENDENCIA", 0))
c4.metric("Reprovado", kpi.get("REPROVADO", 0))

c5, c6, c7, c8 = st.columns(4)
c5.metric("Aprovado", kpi.get("APROVADO", 0))
c6.metric("Aprovado Bacen", kpi.get("APROVADO_BACEN", 0))
c7.metric("Desistiu", kpi.get("DESISTIU", 0))
c8.metric("Leads no Funil", len(df))

c9, c10 = st.columns(2)
c9.metric("Vendas Informadas", (df_vendas_validas["STATUS_BASE"] == "VENDA_INFORMADA").sum())
c10.metric("Vendas Geradas", (df_vendas_validas["STATUS_BASE"] == "VENDA_GERADA").sum())

# =========================================================
# PERFORMANCE POR ORIGEM + CONVERSÃO
# =========================================================
st.subheader("📈 Performance e Conversão por Origem")

origens = ["TODAS"] + sorted(df["ORIGEM"].unique())
origem_sel = st.selectbox("Origem", origens)

df_o = df if origem_sel == "TODAS" else df[df["ORIGEM"] == origem_sel]

leads = len(df_o)
analises = (df_o["STATUS_BASE"] == "ANALISE").sum()
aprovados = (df_o["STATUS_BASE"] == "APROVADO").sum()
vendas = df_o["STATUS_BASE"].isin(["VENDA_GERADA", "VENDA_INFORMADA"]).sum()

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
# AUDITORIA DE CLIENTE
# =========================================================
st.subheader("🔎 Auditoria Rápida de Cliente")

busca = st.text_input("Digite o nome do cliente")

if busca:
    hist = df[df["NOME_CLIENTE"].str.contains(busca.upper(), na=False)]
    if not hist.empty:
        st.dataframe(
            hist.sort_values("DIA")[[
                "DIA", "STATUS_BASE", "ORIGEM", "CAMPANHA", "CORRETOR", "EQUIPE"
            ]],
            use_container_width=True
        )
