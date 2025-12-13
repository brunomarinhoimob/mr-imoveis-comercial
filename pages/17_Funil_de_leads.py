import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Funil de Leads",
    layout="wide"
)

st.title("📊 Funil de Leads – Origem, Status e Conversão")

# =========================
# FUNÇÕES AUXILIARES
# =========================

def normalizar_nome(nome):
    if pd.isna(nome):
        return ""
    return (
        str(nome)
        .upper()
        .strip()
        .replace("  ", " ")
    )


@st.cache_data(ttl=1800)  # cache 30 minutos
def carregar_planilha():
    df = pd.read_csv(
        "https://docs.google.com/spreadsheets/d/SEU_ID_AQUI/export?format=csv",
        dtype=str
    )

    df.columns = [c.upper().strip() for c in df.columns]

    df["NOME_CLIENTE"] = df["CLIENTE"].apply(normalizar_nome)
    df["STATUS_BASE"] = df["SITUAÇÃO"].str.upper().str.strip()

    df["DIA"] = pd.to_datetime(df["DATA"], errors="coerce")

    df = df.dropna(subset=["DIA"])

    return df


@st.cache_data(ttl=1800)
def carregar_crm_ultimos_1000():
    # Exemplo – adapte para sua função real de CRM
    df = pd.read_json("teste_leads.json")

    df.columns = [c.lower() for c in df.columns]

    df["NOME_CLIENTE"] = df["nome_pessoa"].apply(normalizar_nome)
    df["ORIGEM"] = df.get("nome_origem", "SEM ORIGEM").fillna("SEM ORIGEM").str.upper()
    df["CAMPANHA"] = df.get("nome_campanha", "").fillna("").str.upper()
    df["CORRETOR"] = df.get("nome_corretor", "SEM CORRETOR").fillna("SEM CORRETOR").str.upper()
    df["EQUIPE"] = df.get("nome_equipe", "SEM EQUIPE").fillna("SEM EQUIPE").str.upper()

    return df.tail(1000)


# =========================
# CARGA DE DADOS
# =========================

df_plan = carregar_planilha()
df_crm = carregar_crm_ultimos_1000()

# =========================
# FILTRO DE DATA (CORRIGIDO)
# =========================

if df_plan.empty:
    st.warning("Sem dados na planilha.")
    st.stop()

data_inicio, data_fim = st.date_input(
    "📅 Período",
    value=(df_plan["DIA"].min().date(), df_plan["DIA"].max().date()),
    min_value=df_plan["DIA"].min().date(),
    max_value=df_plan["DIA"].max().date(),
)

df_plan = df_plan[
    (df_plan["DIA"].dt.date >= data_inicio) &
    (df_plan["DIA"].dt.date <= data_fim)
]

# =========================
# DEDUP – ÚLTIMO STATUS DO LEAD
# =========================

df_plan = df_plan.sort_values("DIA")
df_plan = df_plan.groupby("NOME_CLIENTE", as_index=False).last()

# =========================
# KPI MACRO
# =========================

st.subheader("📌 Status Atual do Funil")

col1, col2, col3, col4 = st.columns(4)

def kpi(col, titulo, valor):
    col.metric(titulo, int(valor))

kpi(col1, "Em Análise", (df_plan["STATUS_BASE"] == "EM ANÁLISE").sum())
kpi(col1, "Reanálises", (df_plan["STATUS_BASE"] == "REANÁLISE").sum())

kpi(col2, "Aprovados", (df_plan["STATUS_BASE"] == "APROVAÇÃO").sum())
kpi(col2, "Aprovados Bacen", (df_plan["STATUS_BASE"] == "APROVADO BACEN").sum())

kpi(col3, "Pendências", (df_plan["STATUS_BASE"] == "PENDÊNCIA").sum())
kpi(col3, "Reprovados", (df_plan["STATUS_BASE"] == "REPROVAÇÃO").sum())

kpi(col4, "Vendas Geradas", (df_plan["STATUS_BASE"] == "VENDA GERADA").sum())
kpi(col4, "Vendas Informadas", (df_plan["STATUS_BASE"] == "VENDA INFORMADA").sum())

st.metric(
    "Leads no Funil",
    df_plan[~df_plan["STATUS_BASE"].isin(["DESISTIU", "VENDA GERADA"])].shape[0]
)

# =========================
# PERFORMANCE POR ORIGEM
# =========================

st.divider()
st.subheader("📍 Performance por Origem")

df_merge = df_plan.merge(
    df_crm[["NOME_CLIENTE", "ORIGEM", "CAMPANHA", "CORRETOR", "EQUIPE"]],
    on="NOME_CLIENTE",
    how="left"
)

df_merge["ORIGEM"] = df_merge["ORIGEM"].fillna("SEM CADASTRO NO CRM")

origens = ["TODAS"] + sorted(df_merge["ORIGEM"].unique().tolist())
origem_sel = st.selectbox("Selecione a Origem", origens)

if origem_sel != "TODAS":
    df_filtro = df_merge[df_merge["ORIGEM"] == origem_sel]
else:
    df_filtro = df_merge.copy()

colA, colB, colC, colD = st.columns(4)

kpi(colA, "Leads", len(df_filtro))
kpi(colA, "Análises", (df_filtro["STATUS_BASE"] == "EM ANÁLISE").sum())

kpi(colB, "Aprovados", (df_filtro["STATUS_BASE"] == "APROVAÇÃO").sum())
kpi(colB, "Vendas Geradas", (df_filtro["STATUS_BASE"] == "VENDA GERADA").sum())

kpi(colC, "Pendências", (df_filtro["STATUS_BASE"] == "PENDÊNCIA").sum())
kpi(colC, "Reprovados", (df_filtro["STATUS_BASE"] == "REPROVAÇÃO").sum())

kpi(colD, "Desistidos", (df_filtro["STATUS_BASE"] == "DESISTIU").sum())

# =========================
# CONVERSÕES
# =========================

st.divider()
st.subheader("📈 Conversões")

total_leads = len(df_filtro)
analises = (df_filtro["STATUS_BASE"] == "EM ANÁLISE").sum()
aprovados = (df_filtro["STATUS_BASE"] == "APROVAÇÃO").sum()
vendas = (df_filtro["STATUS_BASE"] == "VENDA GERADA").sum()

def taxa(num, den):
    return f"{(num/den*100):.1f}%" if den > 0 else "0%"

c1, c2, c3 = st.columns(3)

c1.metric("Leads → Análise", taxa(analises, total_leads))
c2.metric("Análise → Aprovação", taxa(aprovados, analises))
c3.metric("Aprovação → Venda", taxa(vendas, aprovados))

# =========================
# BUSCA DE CLIENTE
# =========================

st.divider()
st.subheader("🔎 Auditoria de Cliente")

cliente_busca = st.text_input("Digite o nome do cliente")

if cliente_busca:
    nome_busca = normalizar_nome(cliente_busca)
    df_cliente = df_merge[df_merge["NOME_CLIENTE"].str.contains(nome_busca)]

    if df_cliente.empty:
        st.info("Cliente não encontrado.")
    else:
        st.dataframe(df_cliente, use_container_width=True)
