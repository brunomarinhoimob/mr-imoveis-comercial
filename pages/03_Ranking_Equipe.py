import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import date, timedelta

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Ranking por Equipe – MR Imóveis",
    page_icon="👥",
    layout="wide",
)

st.title("👥 Ranking por Equipe – MR Imóveis")

st.caption(
    "Filtre o período para ver o ranking das equipes em análises, aprovações, "
    "vendas e VGV (contando apenas 1 venda por cliente, pela última movimentação)."
)

# ---------------------------------------------------------
# CONFIG: LINK DA PLANILHA
# ---------------------------------------------------------
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID_ANALISES = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ANALISES}"

# ---------------------------------------------------------
# FUNÇÃO AUXILIAR PARA LIMPAR DATA
# ---------------------------------------------------------
def limpar_para_data(serie):
    dt = pd.to_datetime(serie, dayfirst=True, errors="coerce")
    return dt.dt.date

# ---------------------------------------------------------
# CARREGAR E PREPARAR DADOS
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def carregar_dados():
    df = pd.read_csv(CSV_URL)

    df.columns = [c.strip().upper() for c in df.columns]

    # DATA
    if "DATA" in df.columns:
        df["DIA"] = limpar_para_data(df["DATA"])
    elif "DIA" in df.columns:
        df["DIA"] = limpar_para_data(df["DIA"])
    else:
        df["DIA"] = pd.NaT

    # EQUIPE / CORRETOR
    for col in ["EQUIPE", "CORRETOR"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .fillna("NÃO INFORMADO")
                .astype(str)
                .str.upper()
                .str.strip()
            )
        else:
            df[col] = "NÃO INFORMADO"

    # STATUS
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
        status = df[col_situacao].fillna("").astype(str).str.upper()
        df.loc[status.str.contains("EM ANÁLISE"), "STATUS_BASE"] = "EM ANÁLISE"
        df.loc[status.str.contains("REANÁLISE"), "STATUS_BASE"] = "REANÁLISE"
        df.loc[status.str.contains("APROV"), "STATUS_BASE"] = "APROVADO"
        df.loc[status.str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
        df.loc[status.str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA GERADA"
        df.loc[status.str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA INFORMADA"

    # VGV
    if "OBSERVAÇÕES" in df.columns:
        df["VGV"] = pd.to_numeric(df["OBSERVAÇÕES"], errors="coerce").fillna(0.0)
    else:
        df["VGV"] = 0.0

    # -----------------------------
    # NOME / CPF / CHAVE CLIENTE
    # -----------------------------
    possiveis_nome = ["NOME", "CLIENTE", "NOME CLIENTE", "NOME DO CLIENTE"]
    possiveis_cpf = ["CPF", "CPF CLIENTE", "CPF DO CLIENTE"]

    col_nome = None
    for c in possiveis_nome:
        if c in df.columns:
            col_nome = c
            break

    col_cpf = None
    for c in possiveis_cpf:
        if c in df.columns:
            col_cpf = c
            break

    if col_nome is None:
        df["NOME_CLIENTE_BASE"] = "NÃO INFORMADO"
    else:
        df["NOME_CLIENTE_BASE"] = (
            df[col_nome].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
        )

    if col_cpf is None:
        df["CPF_CLIENTE_BASE"] = ""
    else:
        df["CPF_CLIENTE_BASE"] = (
            df[col_cpf]
            .fillna("")
            .astype(str)
            .str.replace(r"\D", "", regex=True)
        )

    df["CHAVE_CLIENTE"] = (
        df["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO")
        + " | "
        + df["CPF_CLIENTE_BASE"].fillna("")
    )

    return df


df = carregar_dados()

if df.empty:
    st.error("Não foi possível carregar dados.")
    st.stop()

# ---------------------------------------------------------
# FILTRO DE PERÍODO (ULTIMOS 30 DIAS EDITÁVEIS)
# ---------------------------------------------------------
st.sidebar.title("Filtros 🔎")

dias_validos = pd.Series(df["DIA"].dropna())

if dias_validos.empty:
    data_min = data_max = date.today()
else:
    data_min = dias_validos.min()
    data_max = dias_validos.max()

# Padrão = últimos 30 dias
default_ini = data_max - timedelta(days=30)
if default_ini < data_min:
    default_ini = data_min

if "rank_eq_periodo" not in st.session_state:
    st.session_state["rank_eq_periodo"] = (default_ini, data_max)

periodo = st.sidebar.date_input(
    "Período (padrão: últimos 30 dias)",
    value=st.session_state["rank_eq_periodo"],
    min_value=data_min,
    max_value=data_max,
)

# Validação
if isinstance(periodo, (tuple, list)) and len(periodo) == 2:
    data_ini, data_fim = periodo
else:
    data_ini, data_fim = default_ini, data_max

st.session_state["rank_eq_periodo"] = (data_ini, data_fim)

# ---------------------------------------------------------
# APLICA FILTRO DE DATA
# ---------------------------------------------------------
df_periodo = df[(df["DIA"] >= data_ini) & (df["DIA"] <= data_fim)]

registros_filtrados = len(df_periodo)

st.caption(
    f"Período filtrado: **{data_ini.strftime('%d/%m/%Y')}** → "
    f"**{data_fim.strftime('%d/%m/%Y')}** • Registros: **{registros_filtrados}**"
)

if df_periodo.empty:
    st.warning("Nenhum registro neste período.")
    st.stop()

# ---------------------------------------------------------
# AGRUPAMENTO POR EQUIPE
# ---------------------------------------------------------
def conta_analises(s):
    return s.isin(["EM ANÁLISE", "REANÁLISE"]).sum()

def conta_aprovacoes(s):
    return (s == "APROVADO").sum()

# --------- BASE 1: ANÁLISE/APROVAÇÃO (POR LINHA) ----------
base_analise = (
    df_periodo.groupby("EQUIPE")
    .agg(
        ANALISES=("STATUS_BASE", conta_analises),
        APROVACOES=("STATUS_BASE", conta_aprovacoes),
    )
    .reset_index()
)

# --------- BASE 2: VENDAS/VGV (POR CLIENTE, 1 VENDA) ------
# Ordena por data para pegar a última movimentação do cliente no período
df_ord = df_periodo.sort_values("DIA")

df_ult = (
    df_ord
    .dropna(subset=["CHAVE_CLIENTE"])
    .groupby("CHAVE_CLIENTE", as_index=False)
    .tail(1)
)

# Considera venda se o status final for VENDA INFORMADA ou VENDA GERADA
mask_venda_final = df_ult["STATUS_BASE"].isin(["VENDA INFORMADA", "VENDA GERADA"])
df_vendas_clientes = df_ult[mask_venda_final].copy()

vendas_eq = (
    df_vendas_clientes
    .groupby("EQUIPE")
    .agg(
        VENDAS=("STATUS_BASE", "size"),
        VGV=("VGV", "sum"),
    )
    .reset_index()
)

# --------- JUNTA AS BASES ----------
rank_eq = pd.merge(base_analise, vendas_eq, on="EQUIPE", how="left")

rank_eq["VENDAS"] = rank_eq["VENDAS"].fillna(0).astype(int)
rank_eq["VGV"] = rank_eq["VGV"].fillna(0.0)

# Remove equipes zeradas
rank_eq = rank_eq[
    (rank_eq["ANALISES"] > 0)
    | (rank_eq["APROVACOES"] > 0)
    | (rank_eq["VENDAS"] > 0)
    | (rank_eq["VGV"] > 0)
]

if rank_eq.empty:
    st.info("Nenhuma equipe teve movimentação neste período.")
    st.stop()

# Taxas
rank_eq["TAXA_APROV_ANALISES"] = np.where(
    rank_eq["ANALISES"] > 0,
    rank_eq["APROVACOES"] / rank_eq["ANALISES"] * 100,
    0,
)

rank_eq["TAXA_VENDAS_ANALISES"] = np.where(
    rank_eq["ANALISES"] > 0,
    rank_eq["VENDAS"] / rank_eq["ANALISES"] * 100,
    0,
)

# Ordenação
rank_eq = rank_eq.sort_values(["VENDAS", "VGV"], ascending=False).reset_index(drop=True)

# ---------------------------------------------------------
# ESTILO VISUAL DA TABELA
# ---------------------------------------------------------
st.markdown("### 📋 Tabela de Ranking das Equipes")

def zebra(row):
    cor = "#0b1120" if row.name % 2 else "#020617"
    return [f"background-color: {cor}"] * len(row)

def highlight_top3(row):
    if row.name == 0:
        return ["background-color: rgba(250, 204, 21, .25); font-weight:bold;"] * len(row)
    if row.name == 1:
        return ["background-color: rgba(148, 163, 184, .15); font-weight:bold;"] * len(row)
    if row.name == 2:
        return ["background-color: rgba(248, 250, 252, .08); font-weight:bold;"] * len(row)
    return [""] * len(row)

# Linha TOTAL imobiliária
total_row = pd.DataFrame({
    "EQUIPE": ["TOTAL IMOBILIÁRIA"],
    "ANALISES": [rank_eq["ANALISES"].sum()],
    "APROVACOES": [rank_eq["APROVACOES"].sum()],
    "VENDAS": [rank_eq["VENDAS"].sum()],
    "VGV": [rank_eq["VGV"].sum()],
    "TAXA_APROV_ANALISES": [
        (rank_eq["APROVACOES"].sum() / rank_eq["ANALISES"].sum() * 100)
        if rank_eq["ANALISES"].sum() > 0 else 0
    ],
    "TAXA_VENDAS_ANALISES": [
        (rank_eq["VENDAS"].sum() / rank_eq["ANALISES"].sum() * 100)
        if rank_eq["ANALISES"].sum() > 0 else 0
    ],
})

rank_eq_table = pd.concat([rank_eq, total_row], ignore_index=True)

styles = [
    {
        "selector": "th",
        "props": [
            ("background-color", "#0f172a"),
            ("color", "#e5e7eb"),
            ("padding", "6px"),
            ("text-align", "center"),
            ("font-weight", "bold"),
        ],
    },
    {
        "selector": "tbody td",
        "props": [
            ("padding", "6px"),
            ("border", "0px"),
            ("font-size", "0.9rem"),
        ],
    },
]

styled = (
    rank_eq_table
    .style
    .format({
        "VGV": "R$ {:,.2f}".format,
        "TAXA_APROV_ANALISES": "{:.1f}%".format,
        "TAXA_VENDAS_ANALISES": "{:.1f}%".format,
    })
    .set_table_styles(styles)
    .apply(zebra, axis=1)
    .apply(highlight_top3, axis=1)
)

st.dataframe(styled, use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# GRÁFICO
# ---------------------------------------------------------
st.markdown("### 💰 VGV por equipe")

chart = (
    alt.Chart(rank_eq)
    .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
    .encode(
        x=alt.X("VGV:Q", title="VGV (R$)"),
        y=alt.Y("EQUIPE:N", sort="-x", title="Equipe"),
        tooltip=[
            "EQUIPE",
            "ANALISES",
            "APROVACOES",
            "VENDAS",
            alt.Tooltip("VGV:Q", title="VGV"),
            alt.Tooltip("TAXA_APROV_ANALISES:Q", title="% Aprov.", format=".1f"),
            alt.Tooltip("TAXA_VENDAS_ANALISES:Q", title="% Vendas", format=".1f"),
        ],
    )
    .properties(height=450)
)

st.altair_chart(chart, use_container_width=True)

st.markdown(
    "<hr><p style='text-align:center;color:#6b7280;'>"
    "Ranking por equipe baseado em análises, aprovações e vendas (1 por cliente) com VGV."
    "</p>",
    unsafe_allow_html=True,
)
