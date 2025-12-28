# =========================================================
# FUNIL DE LEADS – CONVERSÃO POR ORIGEM (EVENTO REAL)
# =========================================================

import streamlit as st
import pandas as pd
import requests
from datetime import date
from utils.supremo_config import TOKEN_SUPREMO

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="Funil de Leads | MR Imóveis",
    page_icon="📊",
    layout="wide"
)

# =========================================================
# TOPO – LOGO
# =========================================================
st.image("logo_mr.png", width=180)
st.title("📊 FUNIL DE LEADS")

# =========================================================
# PLANILHA
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
    p = str(label).upper().split()
    if len(p) < 2:
        return pd.NaT
    mes = MESES.get(p[0])
    try:
        ano = int(p[-1])
    except:
        return pd.NaT
    if not mes:
        return pd.NaT
    return date(ano, mes, 1)

# =========================================================
# CARGA PLANILHA
# =========================================================
@st.cache_data(ttl=300)
def carregar_planilha():
    df = pd.read_csv(CSV_URL, dtype=str)
    df.columns = df.columns.str.upper().str.strip()

    for col in ["CLIENTE", "CORRETOR", "EQUIPE", "SITUAÇÃO", "DATA", "ORIGEM"]:
        if col not in df.columns:
            df[col] = ""

    df["DATA"] = parse_data(df["DATA"])
    df = df.dropna(subset=["DATA"])

    df["DATA_BASE_LABEL"] = df.get("DATA BASE", "").astype(str).str.strip()
    df["DATA_BASE_DATE"] = df["DATA_BASE_LABEL"].apply(parse_data_base)

    for col in ["CLIENTE", "CORRETOR", "EQUIPE", "ORIGEM"]:
        df[col] = df[col].astype(str).str.upper().str.strip()

    df["STATUS_RAW"] = df["SITUAÇÃO"].astype(str).str.upper().str.strip()
    df["STATUS_BASE"] = ""

    regras = [
        ("APROVADO BACEN", "APROVADO_BACEN"),
        ("EM ANÁLISE", "ANALISE"),
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
# CARGA CRM (ORIGEM DO LEAD)
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

    if not dados:
        return pd.DataFrame(columns=["CLIENTE", "ORIGEM_CRM"])

    df = pd.DataFrame(dados)
    df["CLIENTE"] = df["nome_pessoa"].astype(str).str.upper().str.strip()
    df["ORIGEM_CRM"] = df.get("nome_origem", "") \
                         .fillna("") \
                         .astype(str).str.upper().str.strip()

    return df[["CLIENTE", "ORIGEM_CRM"]]

# =========================================================
# DATASETS
# =========================================================
df_hist = carregar_planilha()
df_crm = carregar_crm()

# =========================================================
# ORIGEM FINAL (PLANILHA > CRM > SEM CADASTRO)
# =========================================================
df_hist = df_hist.merge(df_crm, on="CLIENTE", how="left")

df_hist["ORIGEM"] = df_hist["ORIGEM"].where(
    df_hist["ORIGEM"] != "",
    df_hist["ORIGEM_CRM"]
)

df_hist["ORIGEM"] = df_hist["ORIGEM"].replace("", "SEM CADASTRO NO CRM")
df_hist["ORIGEM"] = df_hist["ORIGEM"].fillna("SEM CADASTRO NO CRM")

# =========================================================
# FILTROS
# =========================================================
st.sidebar.header("Filtros")

modo = st.sidebar.radio("Modo de período", ["DIA", "DATA BASE"])
df_f = df_hist.copy()

if modo == "DIA":
    ini, fim = st.sidebar.date_input(
        "Período",
        value=(df_f["DATA"].min().date(), df_f["DATA"].max().date())
    )
    df_f = df_f[
        (df_f["DATA"].dt.date >= ini) &
        (df_f["DATA"].dt.date <= fim)
    ]
else:
    bases = sorted(df_f["DATA_BASE_LABEL"].dropna().unique(), key=parse_data_base)
    sel = st.sidebar.multiselect("Data Base", bases, default=bases)
    if sel:
        df_f = df_f[df_f["DATA_BASE_LABEL"].isin(sel)]

equipe = st.sidebar.selectbox("Equipe", ["TODAS"] + sorted(df_f["EQUIPE"].unique()))
if equipe != "TODAS":
    df_f = df_f[df_f["EQUIPE"] == equipe]

corretor = st.sidebar.selectbox("Corretor", ["TODOS"] + sorted(df_f["CORRETOR"].unique()))
if corretor != "TODOS":
    df_f = df_f[df_f["CORRETOR"] == corretor]

# =========================================================
# KPI – EVENTO REAL
# =========================================================
kpi = st.radio(
    "Selecione o KPI",
    [
        "ANÁLISES",
        "APROVADO",
        "APROVADO BACEN",
        "VENDA GERADA",
        "VENDAS (GERADA + INFORMADA)"
    ],
    horizontal=True
)

if kpi == "ANÁLISES":
    status_kpi = ["ANALISE"]   # 🔥 SEM REANÁLISE
elif kpi == "APROVADO":
    status_kpi = ["APROVADO"]
elif kpi == "APROVADO BACEN":
    status_kpi = ["APROVADO_BACEN"]
elif kpi == "VENDA GERADA":
    status_kpi = ["VENDA_GERADA"]
else:
    status_kpi = ["VENDA_GERADA", "VENDA_INFORMADA"]

df_kpi = df_f[df_f["STATUS_BASE"].isin(status_kpi)]
total_kpi = len(df_kpi)

st.subheader(f"🎯 {kpi} por Origem — Total: {total_kpi}")

if total_kpi == 0:
    st.warning("Nenhum registro para o KPI selecionado.")
    st.stop()

# =========================================================
# CARDS POR ORIGEM
# =========================================================
dist = (
    df_kpi
    .groupby("ORIGEM")
    .size()
    .reset_index(name="QTDE")
    .sort_values("QTDE", ascending=False)
)

dist["PERC"] = (dist["QTDE"] / total_kpi * 100).round(1)

cols = st.columns(4)
i = 0
for _, row in dist.iterrows():
    with cols[i]:
        st.metric(
            label=row["ORIGEM"],
            value=int(row["QTDE"]),
            delta=f'{row["PERC"]}%'
        )
    i += 1
    if i == 4:
        cols = st.columns(4)
        i = 0

# =========================================================
# TABELA DETALHADA
# =========================================================
st.divider()
st.subheader("📋 Eventos do KPI Selecionado")

tabela = df_kpi[
    ["CLIENTE", "CORRETOR", "EQUIPE", "ORIGEM", "STATUS_BASE", "DATA"]
].sort_values("DATA", ascending=False)

st.dataframe(tabela, use_container_width=True)
