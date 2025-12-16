# =========================================================
# FUNIL DE LEADS — INTELIGÊNCIA COMERCIAL
# =========================================================

import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta
from utils.supremo_config import TOKEN_SUPREMO

# =========================================================
# SEGURANÇA
# =========================================================
if "logado" not in st.session_state or not st.session_state.logado:
    st.warning("🔒 Acesso restrito. Faça login para continuar.")
    st.stop()

st.set_page_config(
    page_title="Funil de Leads | Inteligência Comercial",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Funil de Leads — Inteligência Comercial")
st.caption("Visão estratégica por Origem, Equipe e Corretor")

# =========================================================
# PLANILHA (FUNIL)
# =========================================================
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=300)
def carregar_planilha():
    df = pd.read_csv(CSV_URL, dtype=str)
    df.columns = df.columns.str.upper().str.strip()

    for col in ["CLIENTE", "CORRETOR", "EQUIPE", "SITUAÇÃO", "DATA"]:
        if col not in df.columns:
            df[col] = ""

    df["DATA"] = pd.to_datetime(df["DATA"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["DATA"])

    for col in ["CLIENTE", "CORRETOR", "EQUIPE"]:
        df[col] = df[col].astype(str).str.upper().str.strip()

    df["STATUS_RAW"] = df["SITUAÇÃO"].astype(str).str.upper()
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
# CRM — LEADS RECEBIDOS
# =========================================================
@st.cache_data(ttl=1800, show_spinner=False)
def carregar_crm(data_ini, data_fim):
    url = "https://api.supremocrm.com.br/v1/leads"
    headers = {"Authorization": f"Bearer {TOKEN_SUPREMO}"}

    dados = []
    pagina = 1
    LIMITE_PAGINAS = 10
    TIMEOUT = 30

    while pagina <= LIMITE_PAGINAS:
        try:
            r = requests.get(
                url,
                headers=headers,
                params={
                    "pagina": pagina,
                    "data_inicio": data_ini.strftime("%Y-%m-%d"),
                    "data_fim": data_fim.strftime("%Y-%m-%d"),
                },
                timeout=TIMEOUT
            )

            if r.status_code != 200:
                break

            js = r.json()
            if not js.get("data"):
                break

            dados.extend(js["data"])
            pagina += 1

        except requests.exceptions.RequestException:
            break

    if not dados:
        return pd.DataFrame(
            columns=["CLIENTE", "ORIGEM", "CAMPANHA", "DATA_CRM", "CORRETOR", "EQUIPE"]
        )

    df = pd.DataFrame(dados)

    # CLIENTE
    df["CLIENTE"] = df.get("nome_pessoa", "").astype(str).str.upper().str.strip()

    # ORIGEM
    if "nome_origem" in df.columns:
        df["ORIGEM"] = df["nome_origem"].fillna("SEM ORIGEM").astype(str).str.upper()
    else:
        df["ORIGEM"] = "SEM ORIGEM"

    # CAMPANHA
    if "nome_campanha" in df.columns:
        df["CAMPANHA"] = df["nome_campanha"].fillna("-").astype(str).str.upper()
    else:
        df["CAMPANHA"] = "-"

    # DATA CRM
    df["DATA_CRM"] = pd.to_datetime(df.get("data_captura"), errors="coerce")

    # CORRETOR
    if "nome_corretor" in df.columns:
        df["CORRETOR"] = df["nome_corretor"].fillna("SEM CORRETOR").astype(str).str.upper()
    else:
        df["CORRETOR"] = "SEM CORRETOR"

    # EQUIPE
    if "nome_equipe" in df.columns:
        df["EQUIPE"] = (
            df["nome_equipe"]
            .fillna("SEM EQUIPE")
            .astype(str)
            .str.upper()
        )
    else:
        df["EQUIPE"] = "SEM EQUIPE"

    return df[["CLIENTE", "ORIGEM", "CAMPANHA", "DATA_CRM", "CORRETOR", "EQUIPE"]]

# =========================================================
# BASE FUNIL (PLANILHA)
# =========================================================
df_funil = carregar_planilha()

df_status_final = (
    df_funil.sort_values("DATA")
    .groupby("CLIENTE", as_index=False)
    .last()
)

# =========================================================
# PERÍODO PADRÃO (INDEPENDENTE)
# =========================================================
fim = date.today()
ini = fim - timedelta(days=30)

# =========================================================
# FILTROS
# =========================================================
st.sidebar.header("Filtros")

ini, fim = st.sidebar.date_input(
    "Período",
    value=(ini, fim)
)

# =========================================================
# CARREGAMENTO DO CRM
# =========================================================
with st.spinner("🔄 Carregando leads do CRM (período selecionado)..."):
    df_crm = carregar_crm(ini, fim)

# =========================================================
# BASE CONSOLIDADA
# =========================================================
df_base = df_crm.merge(
    df_status_final[["CLIENTE", "STATUS_BASE"]],
    on="CLIENTE",
    how="left"
)

df_base["STATUS_BASE"] = df_base["STATUS_BASE"].fillna("SEM_ACAO")

# =========================================================
# KPIs GERAIS
# =========================================================
def kpis(df):
    return (
        df["CLIENTE"].nunique(),
        df[df["STATUS_BASE"] == "ANALISE"]["CLIENTE"].nunique(),
        df[df["STATUS_BASE"] == "APROVADO"]["CLIENTE"].nunique(),
        df[df["STATUS_BASE"] == "VENDA_GERADA"]["CLIENTE"].nunique(),
    )

leads, analises, aprovados, vendas = kpis(df_base)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Leads CRM", leads)
c2.metric("Análises", analises)
c3.metric("Aprovados", aprovados)
c4.metric("Vendas", vendas)

# =========================================================
# RANKING POR ORIGEM
# =========================================================
st.subheader("🏆 Ranking por Origem")

ranking = df_base.groupby("ORIGEM").apply(
    lambda x: pd.Series({
        "Leads": x["CLIENTE"].nunique(),
        "Análises": x[x["STATUS_BASE"] == "ANALISE"]["CLIENTE"].nunique(),
        "Aprovados": x[x["STATUS_BASE"] == "APROVADO"]["CLIENTE"].nunique(),
        "Vendas": x[x["STATUS_BASE"] == "VENDA_GERADA"]["CLIENTE"].nunique(),
    })
).reset_index()

ranking["% Análise"] = (ranking["Análises"] / ranking["Leads"] * 100).round(1)
ranking["% Venda"] = (ranking["Vendas"] / ranking["Leads"] * 100).round(1)

ranking = ranking.sort_values("% Venda", ascending=False)

st.dataframe(ranking, use_container_width=True)
