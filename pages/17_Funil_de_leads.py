# =========================================================
# FUNIL DE LEADS – ORIGEM, STATUS E CONVERSÃO
# REGRA:
# - Análise = SOMENTE "EM ANÁLISE"
# - Reanálise NÃO entra em conversão
# - Aprovado = SOMENTE "APROVADO"
# - Aprovado Bacen NÃO entra em conversão
# =========================================================

import streamlit as st
import pandas as pd
import requests
from datetime import date
from utils.supremo_config import TOKEN_SUPREMO

st.set_page_config(page_title="Funil de Leads", page_icon="📊", layout="wide")
st.title("📊 Funil de Leads")

# =========================================================
# PLANILHA
# =========================================================
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

MESES = {
    "JANEIRO": 1, "FEVEREIRO": 2, "MARÇO": 3, "MARCO": 3,
    "ABRIL": 4, "MAIO": 5, "JUNHO": 6, "JULHO": 7,
    "AGOSTO": 8, "SETEMBRO": 9, "OUTUBRO": 10,
    "NOVEMBRO": 11, "DEZEMBRO": 12,
}

def parse_data(col):
    return pd.to_datetime(col, dayfirst=True, errors="coerce")

def parse_data_base(label):
    try:
        p = label.upper().split()
        return date(int(p[-1]), MESES[p[0]], 1)
    except:
        return pd.NaT

# =========================================================
# CARREGAMENTO PLANILHA
# =========================================================
@st.cache_data(ttl=300)
def carregar_planilha():
    df = pd.read_csv(CSV_URL, dtype=str)
    df.columns = df.columns.str.upper().str.strip()

    df["DATA"] = parse_data(df["DATA"])
    df = df.dropna(subset=["DATA"])

    df["DATA_BASE_LABEL"] = df.get("DATA BASE", "").astype(str).str.strip()
    df["DATA_BASE_DATE"] = df["DATA_BASE_LABEL"].apply(parse_data_base)

    df["CLIENTE"] = df["CLIENTE"].astype(str).str.upper().str.strip()
    df["CORRETOR"] = df["CORRETOR"].astype(str).str.upper().str.strip()
    df["EQUIPE"] = df["EQUIPE"].astype(str).str.upper().str.strip()

    status = df["SITUAÇÃO"].astype(str).str.upper().str.strip()

    df["STATUS_BASE"] = ""
    df.loc[status.str.contains("EM ANÁLISE"), "STATUS_BASE"] = "ANALISE"
    df.loc[status.str.contains("REANÁLISE"), "STATUS_BASE"] = "REANALISE"
    df.loc[status.str.contains("APROVADO BACEN"), "STATUS_BASE"] = "APROVADO_BACEN"
    df.loc[status.str.contains("APROVA"), "STATUS_BASE"] = "APROVADO"
    df.loc[status.str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
    df.loc[status.str.contains("PEND"), "STATUS_BASE"] = "PENDENCIA"
    df.loc[status.str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA_GERADA"
    df.loc[status.str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA_INFORMADA"
    df.loc[status.str.contains("DESIST"), "STATUS_BASE"] = "DESISTIU"

    df = df[df["STATUS_BASE"] != ""]

    # último status do lead
    df = df.sort_values("DATA").groupby("CLIENTE", as_index=False).last()
    return df

# =========================================================
# CRM
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
    if df.empty:
        return pd.DataFrame(columns=["CLIENTE", "ORIGEM", "CAMPANHA"])

    df["CLIENTE"] = df["nome_pessoa"].astype(str).str.upper().str.strip()
    df["ORIGEM"] = df.get("nome_origem", "SEM CRM").fillna("SEM CRM")
    df["CAMPANHA"] = df.get("nome_campanha", "-").fillna("-")

    return df[["CLIENTE", "ORIGEM", "CAMPANHA"]]

# =========================================================
# CARGA
# =========================================================
df = carregar_planilha().merge(carregar_crm(), on="CLIENTE", how="left")
df["ORIGEM"] = df["ORIGEM"].fillna("SEM CRM")

# =========================================================
# FILTROS
# =========================================================
st.sidebar.header("Filtros")

modo = st.sidebar.radio("Período", ["DIA", "DATA BASE"])

df_f = df.copy()

if modo == "DIA":
    ini, fim = st.sidebar.date_input(
        "Intervalo",
        (df_f["DATA"].min().date(), df_f["DATA"].max().date())
    )
    df_f = df_f[(df_f["DATA"].dt.date >= ini) & (df_f["DATA"].dt.date <= fim)]
else:
    bases = sorted(df_f["DATA_BASE_LABEL"].dropna().unique().tolist())
    sel = st.sidebar.multiselect("Data Base", bases, default=bases)
    if sel:
        df_f = df_f[df_f["DATA_BASE_LABEL"].isin(sel)]

# =========================================================
# STATUS – CARDS
# =========================================================
st.subheader("📌 Status Atual")

vc = df_f["STATUS_BASE"].value_counts()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Em Análise", vc.get("ANALISE", 0))
c2.metric("Reanálise", vc.get("REANALISE", 0))
c3.metric("Pendência", vc.get("PENDENCIA", 0))
c4.metric("Reprovado", vc.get("REPROVADO", 0))

c5, c6, c7, c8 = st.columns(4)
c5.metric("Aprovado", vc.get("APROVADO", 0))
c6.metric("Aprovado Bacen", vc.get("APROVADO_BACEN", 0))
c7.metric("Desistiu", vc.get("DESISTIU", 0))
c8.metric("Leads no Funil", len(df_f))

# =========================================================
# CONVERSÃO (REGRA LIMPA)
# =========================================================
st.subheader("📈 Conversão do Funil")

leads = len(df_f)
analises = df_f[df_f["STATUS_BASE"] == "ANALISE"].shape[0]
aprovados = df_f[df_f["STATUS_BASE"] == "APROVADO"].shape[0]
vendas = df_f[df_f["STATUS_BASE"].isin(["VENDA_INFORMADA", "VENDA_GERADA"])].shape[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Leads", leads)
c2.metric("Análises (EM ANÁLISE)", analises)
c3.metric("Aprovados", aprovados)
c4.metric("Vendas", vendas)

c5, c6, c7 = st.columns(3)
c5.metric("Lead → Análise", f"{(analises/leads*100 if leads else 0):.1f}%")
c6.metric("Análise → Aprovação", f"{(aprovados/analises*100 if analises else 0):.1f}%")
c7.metric("Análise → Venda", f"{(vendas/analises*100 if analises else 0):.1f}%")

# =========================================================
# TABELA
# =========================================================
st.subheader("📋 Leads do Período")
st.dataframe(
    df_f[["CLIENTE", "CORRETOR", "EQUIPE", "ORIGEM", "STATUS_BASE", "DATA"]]
    .sort_values("DATA", ascending=False),
    use_container_width=True
)
