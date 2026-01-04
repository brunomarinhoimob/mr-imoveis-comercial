# =========================================================
# FUNIL DE LEADS – CONVERSÃO POR ORIGEM (EVENTO REAL)
# =========================================================

import streamlit as st
import pandas as pd
import requests
from datetime import date
from utils.supremo_config import TOKEN_SUPREMO

# =========================================================
# BLOQUEIO DE LOGIN (IGUAL PÁGINA 03)
# =========================================================
if "logado" not in st.session_state or not st.session_state.logado:
    st.warning("🔒 Acesso restrito. Faça login para continuar.")
    st.stop()

if st.session_state.get("perfil") == "corretor":
    st.warning("🔒 Você não tem permissão para acessar esta página.")
    st.stop()

# =========================================================
# CONFIG DA PÁGINA
# =========================================================
st.set_page_config(
    page_title="Funil de Leads | MR Imóveis",
    page_icon="📊",
    layout="wide"
)

# =========================================================
# TOPO – LOGO E TÍTULO
# =========================================================
try:
    st.image("logo_mr.png", width=180)
except Exception:
    pass

st.title("📊 FUNIL DE LEADS – Conversão por Origem")

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
        df[col] = (
            df[col]
            .fillna("")
            .astype(str)
            .str.upper()
            .str.strip()
        )

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
# CARGA CRM – ORIGEM (LIMITADO / SEGURO)
# =========================================================
@st.cache_data(ttl=1800)
def carregar_crm():
    url = "https://api.supremocrm.com.br/v1/leads"
    headers = {"Authorization": f"Bearer {TOKEN_SUPREMO}"}

    dados, pagina = [], 1
    LIMITE = 300

    try:
        while len(dados) < LIMITE:
            r = requests.get(
                url,
                headers=headers,
                params={"pagina": pagina},
                timeout=30
            )
            if r.status_code != 200:
                break

            js = r.json()
            if not js.get("data"):
                break

            dados.extend(js["data"])
            pagina += 1

    except requests.exceptions.RequestException:
        return pd.DataFrame(columns=["CLIENTE", "ORIGEM_CRM"])

    dados = dados[:LIMITE]

    df = pd.DataFrame(dados)
    df["CLIENTE"] = df.get("nome_pessoa", "").astype(str).str.upper().str.strip()
    df["ORIGEM_CRM"] = df.get("nome_origem", "").fillna("").astype(str).str.upper().str.strip()

    return df[["CLIENTE", "ORIGEM_CRM"]]

# =========================================================
# DATASET FINAL
# =========================================================
df_hist = carregar_planilha()
df_crm = carregar_crm()

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
st.sidebar.title("Filtros 🔎")

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

# ---------- FILTRO EQUIPE ----------
equipes = sorted([e for e in df_f["EQUIPE"].unique() if e and e != "NAN"])
equipe_sel = st.sidebar.selectbox("Equipe", ["TODAS"] + equipes)

if equipe_sel != "TODAS":
    df_f = df_f[df_f["EQUIPE"] == equipe_sel]

# ---------- FILTRO CORRETOR ----------
corretores = sorted([c for c in df_f["CORRETOR"].unique() if c and c != "NAN"])
corretor_sel = st.sidebar.selectbox("Corretor", ["TODOS"] + corretores)

if corretor_sel != "TODOS":
    df_f = df_f[df_f["CORRETOR"] == corretor_sel]

# =========================================================
# KPI
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
    status_kpi = ["ANALISE"]
elif kpi == "APROVADO":
    status_kpi = ["APROVADO"]
elif kpi == "APROVADO BACEN":
    status_kpi = ["APROVADO_BACEN"]
elif kpi == "VENDA GERADA":
    status_kpi = ["VENDA_GERADA"]
else:
    status_kpi = ["VENDA_GERADA", "VENDA_INFORMADA"]

df_kpi = df_f[df_f["STATUS_BASE"].isin(status_kpi)]
total = len(df_kpi)

st.subheader(f"🎯 {kpi} por Origem — Total: {total}")

if total == 0:
    st.warning("Nenhum registro para os filtros selecionados.")
    st.stop()

# =========================================================
# CARDS
# =========================================================
dist = (
    df_kpi.groupby("ORIGEM")
    .size()
    .reset_index(name="QTDE")
    .sort_values("QTDE", ascending=False)
)

dist["PERC"] = (dist["QTDE"] / total * 100).round(1)

cols = st.columns(4)
i = 0
for _, row in dist.iterrows():
    with cols[i]:
        st.metric(row["ORIGEM"], int(row["QTDE"]), f'{row["PERC"]}%')
    i += 1
    if i == 4:
        cols = st.columns(4)
        i = 0

# =========================================================
# TABELA
# =========================================================
st.divider()
st.subheader("📋 Eventos do KPI Selecionado")

st.dataframe(
    df_kpi[
        ["CLIENTE", "CORRETOR", "EQUIPE", "ORIGEM", "STATUS_BASE", "DATA"]
    ].sort_values("DATA", ascending=False),
    use_container_width=True
)
