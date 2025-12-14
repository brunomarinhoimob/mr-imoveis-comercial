# =========================================================
# FUNIL DE LEADS – ORIGEM, STATUS E CONVERSÃO
# =========================================================

import streamlit as st
import pandas as pd
import requests
from datetime import date
from utils.supremo_config import TOKEN_SUPREMO

st.set_page_config(page_title="Funil de Leads", page_icon="📊", layout="wide")
st.title("📊 Funil de Leads – Origem, Status e Conversão")

# =========================================================
# PLANILHA FIXA
# =========================================================
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================
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
        mes, ano = str(label).upper().split()
        return date(int(ano), MESES.get(mes, 1), 1)
    except:
        return pd.NaT

# =========================================================
# CARGA DA PLANILHA
# =========================================================
@st.cache_data(ttl=300)
def carregar_planilha():
    df = pd.read_csv(CSV_URL, dtype=str)
    df.columns = df.columns.str.upper().str.strip()

    df["DATA"] = parse_data(df["DATA"])
    df = df.dropna(subset=["DATA"])

    df["DATA_BASE_LABEL"] = df.get("DATA BASE", "")
    df["DATA_BASE_DATE"] = df["DATA_BASE_LABEL"].apply(parse_data_base_label)

    df["CLIENTE"] = df["CLIENTE"].str.upper().str.strip()
    df["CORRETOR"] = df["CORRETOR"].str.upper().str.strip()
    df["EQUIPE"] = df["EQUIPE"].str.upper().str.strip()

    s = df["SITUAÇÃO"].str.upper()

    df["STATUS_BASE"] = ""
    df.loc[s.str.contains("EM ANÁLISE"), "STATUS_BASE"] = "ANALISE"
    df.loc[s.str.contains("REANÁLISE"), "STATUS_BASE"] = "REANALISE"
    df.loc[s.str.contains("APROVADO BACEN"), "STATUS_BASE"] = "APROVADO_BACEN"
    df.loc[s.str.contains("APROVA"), "STATUS_BASE"] = "APROVADO"
    df.loc[s.str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
    df.loc[s.str.contains("PEND"), "STATUS_BASE"] = "PENDENCIA"
    df.loc[s.str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA_GERADA"
    df.loc[s.str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA_INFORMADA"
    df.loc[s.str.contains("DESIST"), "STATUS_BASE"] = "DESISTIU"

    df = df[df["STATUS_BASE"] != ""]
    df = df.sort_values("DATA").groupby("CLIENTE", as_index=False).last()

    return df

# =========================================================
# CARGA CRM (ROBUSTO)
# =========================================================
@st.cache_data(ttl=900)
def carregar_crm():
    url = "https://api.supremocrm.com.br/v1/leads"
    headers = {"Authorization": f"Bearer {TOKEN_SUPREMO}"}
    dados, pagina = [], 1

    while True:
        r = requests.get(url, headers=headers, params={"page": pagina}, timeout=20)
        if r.status_code != 200:
            break
        bloco = r.json().get("dados", [])
        if not bloco:
            break
        dados.extend(bloco)
        pagina += 1

    if not dados:
        return pd.DataFrame(columns=["CLIENTE", "ORIGEM", "CAMPANHA"])

    df = pd.json_normalize(dados)

    for campo in ["nome_pessoa", "pessoa.nome", "nome"]:
        if campo in df.columns:
            df["CLIENTE"] = df[campo].astype(str).str.upper().str.strip()
            break
    else:
        return pd.DataFrame(columns=["CLIENTE", "ORIGEM", "CAMPANHA"])

    df["ORIGEM"] = df.get("nome_origem", "SEM CADASTRO").fillna("SEM CADASTRO")
    df["CAMPANHA"] = df.get("nome_campanha", "-").fillna("-")

    return df[["CLIENTE", "ORIGEM", "CAMPANHA"]]

# =========================================================
# LOAD
# =========================================================
df = carregar_planilha()
df = df.merge(carregar_crm(), on="CLIENTE", how="left")

df["ORIGEM"] = df["ORIGEM"].fillna("SEM CADASTRO")
df["CAMPANHA"] = df["CAMPANHA"].fillna("-")

# =========================================================
# FILTROS
# =========================================================
st.sidebar.header("Filtros")

modo = st.sidebar.radio("Período", ["DIA", "DATA BASE"])
df_f = df.copy()

if modo == "DIA":
    ini, fim = st.sidebar.date_input(
        "Período",
        value=(df_f["DATA"].min().date(), df_f["DATA"].max().date())
    )
    df_f = df_f[(df_f["DATA"].dt.date >= ini) & (df_f["DATA"].dt.date <= fim)]
else:
    bases = sorted(df_f["DATA_BASE_LABEL"].unique())
    sel = st.sidebar.multiselect("Data Base", bases, default=bases)
    if sel:
        df_f = df_f[df_f["DATA_BASE_LABEL"].isin(sel)]

origens = ["TODAS"] + sorted(df_f["ORIGEM"].unique())
origem_sel = st.selectbox("Origem", origens)
df_o = df_f if origem_sel == "TODAS" else df_f[df_f["ORIGEM"] == origem_sel]

# =========================================================
# STATUS ATUAL
# =========================================================
st.subheader("📌 Status Atual do Funil")

kpi = df_o["STATUS_BASE"].value_counts()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Em Análise", int(kpi.get("ANALISE", 0)))
c2.metric("Reanálise", int(kpi.get("REANALISE", 0)))
c3.metric("Pendência", int(kpi.get("PENDENCIA", 0)))
c4.metric("Reprovado", int(kpi.get("REPROVADO", 0)))

c5, c6, c7, c8 = st.columns(4)
c5.metric("Aprovado", int(kpi.get("APROVADO", 0)))
c6.metric("Aprovado Bacen", int(kpi.get("APROVADO_BACEN", 0)))
c7.metric("Desistiu", int(kpi.get("DESISTIU", 0)))
c8.metric("Leads", len(df_o))

# =========================================================
# PERFORMANCE E CONVERSÃO (PRINT)
# =========================================================
st.subheader("📈 Performance e Conversão")

tipo_venda = st.radio(
    "Tipo de venda para conversão",
    ["VENDAS GERADAS", "VENDAS INFORMADAS", "AMBAS"],
    horizontal=True,
    index=2
)

leads = len(df_o)
analises = (df_o["STATUS_BASE"] == "ANALISE").sum()
aprovados = df_o["STATUS_BASE"].isin(
    ["APROVADO", "VENDA_GERADA", "VENDA_INFORMADA"]
).sum()

if tipo_venda == "VENDAS GERADAS":
    vendas = (df_o["STATUS_BASE"] == "VENDA_GERADA").sum()
elif tipo_venda == "VENDAS INFORMADAS":
    vendas = (df_o["STATUS_BASE"] == "VENDA_INFORMADA").sum()
else:
    vendas = df_o["STATUS_BASE"].isin(
        ["VENDA_GERADA", "VENDA_INFORMADA"]
    ).sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Leads", leads)
c2.metric("Análises (funil)", analises)
c3.metric("Aprovados (funil)", aprovados)
c4.metric("Vendas (funil)", vendas)

c5, c6, c7, c8 = st.columns(4)
c5.metric("Lead → Análise", f"{(analises/leads*100 if leads else 0):.1f}%")
c6.metric("Análise → Aprovação", f"{(aprovados/analises*100 if analises else 0):.1f}%")
c7.metric("Análise → Venda", f"{(vendas/analises*100 if analises else 0):.1f}%")
c8.metric("Aprovação → Venda", f"{(vendas/aprovados*100 if aprovados else 0):.1f}%")

# =========================================================
# TABELA FINAL
# =========================================================
st.divider()
st.subheader("📋 Leads")

tabela = df_o[["CLIENTE", "CORRETOR", "EQUIPE", "STATUS_BASE", "DATA"]] \
    .sort_values("DATA", ascending=False) \
    .rename(columns={"DATA": "ULTIMA_ATUALIZACAO"})

st.dataframe(tabela, use_container_width=True)
