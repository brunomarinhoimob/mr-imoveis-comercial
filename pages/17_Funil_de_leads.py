# =========================================================
# FUNIL DE LEADS – ORIGEM, STATUS E CONVERSÃO
# =========================================================

import streamlit as st
import pandas as pd
import requests
from datetime import date
from utils.supremo_config import TOKEN_SUPREMO

# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================
st.set_page_config(
    page_title="Funil de Leads",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Funil de Leads – Origem, Status e Conversão")

# =========================================================
# PLANILHA (GOOGLE SHEETS)
# =========================================================
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

# =========================================================
# UTILIDADES
# =========================================================
MESES = {
    "JANEIRO": 1, "FEVEREIRO": 2, "MARÇO": 3, "MARCO": 3,
    "ABRIL": 4, "MAIO": 5, "JUNHO": 6, "JULHO": 7,
    "AGOSTO": 8, "SETEMBRO": 9, "OUTUBRO": 10,
    "NOVEMBRO": 11, "DEZEMBRO": 12,
}

def parse_data(col):
    return pd.to_datetime(col, dayfirst=True, errors="coerce")

def parse_data_base(label):
    if pd.isna(label):
        return pd.NaT
    partes = str(label).upper().split()
    if len(partes) < 2:
        return pd.NaT
    mes = MESES.get(partes[0])
    try:
        ano = int(partes[-1])
    except:
        return pd.NaT
    if not mes:
        return pd.NaT
    return date(ano, mes, 1)

# =========================================================
# CARGA DA PLANILHA (HISTÓRICO)
# =========================================================
@st.cache_data(ttl=300)
def carregar_planilha():
    df = pd.read_csv(CSV_URL, dtype=str)
    df.columns = df.columns.str.upper().str.strip()

    # Garante colunas essenciais
    for col in ["CLIENTE", "CORRETOR", "EQUIPE", "SITUAÇÃO", "DATA"]:
        if col not in df.columns:
            df[col] = ""

    df["DATA"] = parse_data(df["DATA"])
    df = df.dropna(subset=["DATA"])

    df["DATA_BASE_LABEL"] = df.get("DATA BASE", "").astype(str).str.strip()
    df["DATA_BASE_DATE"] = df["DATA_BASE_LABEL"].apply(parse_data_base)

    for col in ["CLIENTE", "CORRETOR", "EQUIPE"]:
        df[col] = df[col].astype(str).str.upper().str.strip()

    # Normalização de status
    df["STATUS_RAW"] = df["SITUAÇÃO"].astype(str).str.upper().str.strip()
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

    df = df[df["STATUS_BASE"] != ""]
    return df

# =========================================================
# CARGA DO CRM (SUPREMO)
# =========================================================
@st.cache_data(ttl=1800)
def carregar_crm():
    url = "https://api.supremocrm.com.br/v1/leads"
    headers = {"Authorization": f"Bearer {TOKEN_SUPREMO}"}

    dados = []
    pagina = 1

    while len(dados) < 1000:
        r = requests.get(url, headers=headers, params={"pagina": pagina}, timeout=20)
        if r.status_code != 200:
            break

        js = r.json()
        if not js.get("data"):
            break

        dados.extend(js["data"])
        pagina += 1

    if not dados:
        return pd.DataFrame(columns=["CLIENTE", "ORIGEM", "CAMPANHA"])

    df = pd.DataFrame(dados)

    df["CLIENTE"] = df["nome_pessoa"].astype(str).str.upper().str.strip()
    df["ORIGEM"] = df.get("nome_origem", "SEM CADASTRO NO CRM").fillna("SEM CADASTRO NO CRM")
    df["CAMPANHA"] = df.get("nome_campanha", "-").fillna("-")

    df["ORIGEM"] = df["ORIGEM"].astype(str).str.upper().str.strip()
    df["CAMPANHA"] = df["CAMPANHA"].astype(str).str.upper().str.strip()

    return df[["CLIENTE", "ORIGEM", "CAMPANHA"]]

# =========================================================
# DATASETS UNIFICADOS
# =========================================================
df_hist = carregar_planilha()
df_crm = carregar_crm()

df_hist = df_hist.merge(df_crm, on="CLIENTE", how="left")
df_hist["ORIGEM"] = df_hist["ORIGEM"].fillna("SEM CADASTRO NO CRM")
df_hist["CAMPANHA"] = df_hist["CAMPANHA"].fillna("-")

# =========================================================
# FILTROS (SIDEBAR)
# =========================================================
st.sidebar.header("Filtros")

modo = st.sidebar.radio("Modo de período", ["DIA", "DATA BASE"])
df_f = df_hist.copy()

if modo == "DIA":
    ini, fim = st.sidebar.date_input(
        "Período",
        value=(df_f["DATA"].min().date(), df_f["DATA"].max().date())
    )
    df_f = df_f[(df_f["DATA"].dt.date >= ini) & (df_f["DATA"].dt.date <= fim)]
else:
    bases = sorted(df_f["DATA_BASE_LABEL"].dropna().unique(), key=parse_data_base)
    sel = st.sidebar.multiselect("Data Base", bases, default=bases)
    if sel:
        df_f = df_f[df_f["DATA_BASE_LABEL"].isin(sel)]

# garante coluna CORRETOR para não quebrar seletor
if "CORRETOR" not in df_f.columns:
    df_f["CORRETOR"] = ""

equipe = st.sidebar.selectbox("Equipe", ["TODAS"] + sorted(df_f["EQUIPE"].unique()))
if equipe != "TODAS":
    df_f = df_f[df_f["EQUIPE"] == equipe]

corretor = st.sidebar.selectbox(
    "Corretor",
    ["TODOS"] + sorted(df_f["CORRETOR"].unique())
)
if corretor != "TODOS":
    df_f = df_f[df_f["CORRETOR"] == corretor]

# =========================================================
# STATUS ATUAL (ÚLTIMO STATUS POR LEAD)
# =========================================================
st.subheader("📌 Status Atual do Funil")

df_atual = df_f.sort_values("DATA").groupby("CLIENTE", as_index=False).last()
kpi = df_atual["STATUS_BASE"].value_counts()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Em Análise", int(kpi.get("ANALISE", 0)))
c2.metric("Reanálise", int(kpi.get("REANALISE", 0)))
c3.metric("Pendência", int(kpi.get("PENDENCIA", 0)))
c4.metric("Reprovado", int(kpi.get("REPROVADO", 0)))

c5, c6, c7, c8 = st.columns(4)
c5.metric("Aprovado", int(kpi.get("APROVADO", 0)))
c6.metric("Aprovado Bacen", int(kpi.get("APROVADO_BACEN", 0)))
c7.metric("Desistiu", int(kpi.get("DESISTIU", 0)))
c8.metric("Leads no Funil", len(df_atual))

# =========================================================
# PERFORMANCE E CONVERSÃO POR ORIGEM (ESTOQUE)
# =========================================================
st.subheader("📈 Performance e Conversão por Origem")

origem = st.selectbox("Origem", ["TODAS"] + sorted(df_f["ORIGEM"].unique()))
df_o = df_f if origem == "TODAS" else df_f[df_f["ORIGEM"] == origem]

leads = df_o["CLIENTE"].nunique()
analises = df_o[df_o["STATUS_BASE"] == "ANALISE"]["CLIENTE"].nunique()
aprovados = df_o[df_o["STATUS_BASE"] == "APROVADO"]["CLIENTE"].nunique()
vendas = df_o[df_o["STATUS_BASE"] == "VENDA_GERADA"]["CLIENTE"].nunique()

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
# TABELA FINAL
# =========================================================
st.divider()
st.subheader("📋 Leads")

tabela = df_atual[
    ["CLIENTE", "CORRETOR", "EQUIPE", "ORIGEM", "CAMPANHA", "STATUS_BASE", "DATA"]
].sort_values("DATA", ascending=False)

tabela.rename(columns={"DATA": "ULTIMA_ATUALIZACAO"}, inplace=True)

st.dataframe(tabela, use_container_width=True)
