import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="Produção Comercial",
    page_icon="📞",
    layout="wide"
)

st_autorefresh(interval=30 * 1000, key="auto_refresh_producao")

# CSS
st.markdown("""
<style>
.stApp { background: #020617; }
div[data-testid="stMetric"] { background: linear-gradient(145deg, #0f172a 0%, #020617 100%); border: 1px solid rgba(148,163,184,0.20); padding: 18px; border-radius: 18px; }
div[data-testid="stMetricLabel"] { color: #94a3b8; }
div[data-testid="stMetricValue"] { color: white; }
</style>
""", unsafe_allow_html=True)

# DADOS
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
CSV_PRODUCAO = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=1161609337"
CSV_PROCESSOS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=1574157905"

@st.cache_data(ttl=10)
def carregar_dados():
    df = pd.read_csv(CSV_PRODUCAO)
    df.columns = [c.strip().upper() for c in df.columns]
    df["DATA"] = pd.to_datetime(df["DATA"], dayfirst=True, errors="coerce")
    
    dfp = pd.read_csv(CSV_PROCESSOS)
    dfp.columns = [c.strip().upper() for c in dfp.columns]
    dfp["DATA"] = pd.to_datetime(dfp.get("DATA", dfp.get("DIA")), dayfirst=True, errors="coerce")
    
    # Normalização
    col_status = next((c for c in ["SITUAÇÃO", "SITUACAO", "STATUS"] if c in dfp.columns), "SITUAÇÃO")
    dfp["STATUS_NORMALIZADO"] = dfp[col_status].fillna("").astype(str).str.upper().str.strip()
    dfp["CHAVE_CLIENTE"] = dfp.get("NOME", "").astype(str) + " | " + dfp.get("CPF", "").astype(str)
    return df, dfp

df, df_processos = carregar_dados()

# FILTROS
st.sidebar.title("Filtros 🔎")
data_min, data_max = df["DATA"].min(), df["DATA"].max()
periodo = st.sidebar.date_input("Período", value=(data_min, data_max))

if isinstance(periodo, tuple) and len(periodo) == 2:
    df = df[(df["DATA"].dt.date >= periodo[0]) & (df["DATA"].dt.date <= periodo[1])]
    df_proc_f = df_processos[df_processos["DATA"].dt.date >= periodo[0]]
else:
    df_proc_f = df_processos

# KPIs
df_clientes = df_proc_f.drop_duplicates(subset=["CHAVE_CLIENTE"], keep="last")
analises = int((df_clientes["STATUS_NORMALIZADO"] == "EM ANALISE").sum())
aprovacoes = int((df_clientes["STATUS_NORMALIZADO"] == "APROVADO").sum())
aprovado_bacen = int((df_clientes["STATUS_NORMALIZADO"] == "APROVADO BACEN").sum())
aprovado_restricao = int((df_clientes["STATUS_NORMALIZADO"] == "APROVADO COM RESTRICAO").sum())
vendas = int(df_clientes["STATUS_NORMALIZADO"].isin(["VENDA GERADA", "VENDA INFORMADA"]).sum())

# INTERFACE
st.title("📞 Produção Comercial")
r1, r2, r3, r4, r5 = st.columns(5)
r1.metric("📄 Análises", analises)
r2.metric("✅ Aprovações", aprovacoes)
r3.metric("🟡 Restrição", aprovado_restricao)
r4.metric("🏦 BACEN", aprovado_bacen)
r5.metric("💰 Vendas", vendas)