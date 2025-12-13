# =========================================================
# FUNIL DE LEADS – PERFORMANCE E CONVERSÃO POR ORIGEM
# =========================================================

import streamlit as st
import pandas as pd
from datetime import date
from utils.supremo_config import TOKEN_SUPREMO
import requests

st.set_page_config(page_title="Funil de Leads", layout="wide")
st.title("📈 Performance e Conversão por Origem")

# =========================================================
# PLANILHA (MESMA FONTE)
# =========================================================
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(ttl=300)
def carregar_planilha():
    df = pd.read_csv(CSV_URL, dtype=str)
    df.columns = df.columns.str.upper().str.strip()

    df["DATA"] = pd.to_datetime(df["DATA"], dayfirst=True, errors="coerce")
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

    df = df[df["STATUS_BASE"] != ""]

    # último status do cliente
    df = df.sort_values("DATA")
    df = df.groupby("CLIENTE", as_index=False).last()

    return df

@st.cache_data(ttl=1800)
def carregar_crm():
    url = "https://api.supremocrm.com.br/v1/leads"
    headers = {"Authorization": f"Bearer {TOKEN_SUPREMO}"}
    dados, pagina = [], 1

    while len(dados) < 1000:
        r = requests.get(url, headers=headers, params={"pagina": pagina}, timeout=15)
        if r.status_code != 200:
            break
        js = r.json()
        if not js.get("data"):
            break
        dados.extend(js["data"])
        pagina += 1

    df = pd.DataFrame(dados)
    if df.empty:
        return pd.DataFrame(columns=["CLIENTE", "ORIGEM"])

    df["CLIENTE"] = df["nome_pessoa"].str.upper().str.strip()
    df["ORIGEM"] = df.get("nome_origem", "SEM CADASTRO NO CRM").fillna("SEM CADASTRO NO CRM")
    df["ORIGEM"] = df["ORIGEM"].str.upper().str.strip()

    return df[["CLIENTE", "ORIGEM"]]

# =========================================================
# CARGA
# =========================================================
df = carregar_planilha()
df = df.merge(carregar_crm(), on="CLIENTE", how="left")
df["ORIGEM"] = df["ORIGEM"].fillna("SEM CADASTRO NO CRM")

# =========================================================
# FILTRO ORIGEM
# =========================================================
origem_sel = st.selectbox(
    "Origem",
    ["TODAS"] + sorted(df["ORIGEM"].unique().tolist())
)

df_o = df if origem_sel == "TODAS" else df[df["ORIGEM"] == origem_sel]

# =========================================================
# SELETOR DE TIPO DE VENDA
# =========================================================
tipo_venda = st.radio(
    "Tipo de venda para conversão",
    ["Vendas Informadas + Geradas", "Apenas Vendas Geradas"],
    horizontal=True
)

if tipo_venda == "Apenas Vendas Geradas":
    vendas_df = df_o[df_o["STATUS_BASE"] == "VENDA_GERADA"]
else:
    vendas_df = df_o[df_o["STATUS_BASE"].isin(["VENDA_GERADA", "VENDA_INFORMADA"])]

# =========================================================
# MÉTRICAS CORRETAS
# =========================================================
leads = len(df_o)

analises = df_o[df_o["STATUS_BASE"] == "ANALISE"].shape[0]
reanalises = df_o[df_o["STATUS_BASE"] == "REANALISE"].shape[0]

aprovados = df_o[df_o["STATUS_BASE"].isin([
    "APROVADO", "APROVADO_BACEN", "VENDA_GERADA", "VENDA_INFORMADA"
])].shape[0]

vendas = vendas_df.shape[0]

# =========================================================
# CARDS
# =========================================================
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Leads", leads)
c2.metric("Análises", analises)
c3.metric("Reanálises", reanalises)
c4.metric("Aprovados", aprovados)
c5.metric("Vendas", vendas)

c6, c7, c8, c9 = st.columns(4)
c6.metric("Lead → Análise", f"{(analises/leads*100 if leads else 0):.1f}%")
c7.metric("Análise → Aprovação", f"{(aprovados/analises*100 if analises else 0):.1f}%")
c8.metric("Análise → Venda", f"{(vendas/analises*100 if analises else 0):.1f}%")
c9.metric("Aprovação → Venda", f"{(vendas/aprovados*100 if aprovados else 0):.1f}%")

# =========================================================
# TABELA DE LEADS DA ORIGEM
# =========================================================
st.divider()
st.subheader("📋 Leads da origem selecionada")

tabela = df_o[[
    "CLIENTE", "CORRETOR", "EQUIPE", "STATUS_BASE", "DATA"
]].sort_values("DATA", ascending=False)

st.dataframe(tabela, use_container_width=True)
