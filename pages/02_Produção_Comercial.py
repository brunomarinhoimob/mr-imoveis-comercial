import streamlit as st
import pandas as pd
import altair as alt
import unicodedata
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# =========================================================
# CONFIGURAÇÃO
# =========================================================
st.set_page_config(page_title="Produção Comercial", page_icon="📞", layout="wide")
st_autorefresh(interval=60 * 1000, key="refresh_comercial")

# CSS Otimizado
st.markdown("""
<style>
.stApp { background: #020617; }
div[data-testid="stMetric"] { background: #0f172a; border: 1px solid #334155; padding: 15px; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# GOOGLE SHEETS
# =========================================================
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
CSV_PRODUCAO = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=1161609337"
CSV_PROCESSOS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=1574157905"

# =========================================================
# FUNÇÕES DE NORMALIZAÇÃO
# =========================================================
def remover_acentos(texto):
    if pd.isna(texto): return ""
    texto = str(texto)
    nfkd = unicodedata.normalize('NFKD', texto)
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).upper().strip()

def mes_ano_para_data(valor):
    try:
        partes = str(valor).lower().split()
        meses = {"janeiro":1, "fevereiro":2, "marco":3, "abril":4, "maio":5, "junho":6, "julho":7, "agosto":8, "setembro":9, "outubro":10, "novembro":11, "dezembro":12}
        return datetime(int(partes[-1]), meses.get(partes[0], 1), 1).date()
    except: return None

# =========================================================
# CARREGAR DADOS
# =========================================================
@st.cache_data(ttl=60)
def carregar_tudo():
    df = pd.read_csv(CSV_PRODUCAO)
    dfp = pd.read_csv(CSV_PROCESSOS)
    
    # Limpeza básica
    df.columns = [c.strip().upper() for c in df.columns]
    dfp.columns = [c.strip().upper() for c in dfp.columns]
    
    # Datas
    df["DATA"] = pd.to_datetime(df["DATA"], dayfirst=True, errors="coerce")
    dfp["DATA"] = pd.to_datetime(dfp["DATA"], dayfirst=True, errors="coerce")
    
    # Normalizar Status e Origem
    dfp["STATUS_NORM"] = dfp["SITUAÇÃO"].apply(remover_acentos)
    dfp["ORIGEM_NORM"] = dfp["ORIGEM"].apply(remover_acentos)
    
    return df, dfp

df, dfp = carregar_tudo()

# =========================================================
# FILTROS
# =========================================================
st.title("📞 Produção Comercial Completa")
data_min, data_max = df["DATA"].min().date(), df["DATA"].max().date()
periodo = st.sidebar.date_input("Período", (data_min, data_max))

if len(periodo) == 2:
    df = df[(df["DATA"].dt.date >= periodo[0]) & (df["DATA"].dt.date <= periodo[1])]
    dfp = dfp[(dfp["DATA"].dt.date >= periodo[0])]

# =========================================================
# MÉTRICAS E CARDS
# =========================================================
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Operacional", int(df["TOTAL"].sum()))
col2.metric("Leads Quentes", int(df["LEADS QUENTES"].sum()))
col3.metric("Taxa Prospect", f"{(df['PROSPECT'].sum()/df['TOTAL'].sum()*100):.1f}%")
col4.metric("Total Análises", int(dfp["CHAVE_CLIENTE"].nunique()))

# =========================================================
# RESUMO DE RESULTADOS (ÚLTIMA LINHA)
# =========================================================
st.markdown("---")
st.subheader("🎯 Resultado dos Processos")

dfp_final = dfp.sort_values("DATA").groupby("CHAVE_CLIENTE").last().reset_index()

c5, c6, c7, c8 = st.columns(4)
c5.metric("Em Análise", int(dfp_final["STATUS_NORM"].str.contains("ANALISE").sum()))
c6.metric("Pendências", int(dfp_final["STATUS_NORM"].str.contains("PENDEN").sum()))
c7.metric("Aprovações", int(dfp_final["STATUS_NORM"].str.contains("APROVADO").sum()))
c8.metric("Vendas", int(dfp_final["STATUS_NORM"].str.contains("VENDA").sum()))

# =========================================================
# QUADRO DE ORIGENS (RESUMO)
# =========================================================
st.markdown("---")
st.subheader("🧠 Origens (Análises Ativas)")
origens_map = {"INDICAÇÃO": "INDICACAO", "ORGÂNICO": "ORGANICO", "LISTA": "LISTA", "INSTAGRAM": "INSTA", "TRÁFEGO": "TRAFEGO"}
cols_o = st.columns(len(origens_map))

df_ativas = dfp_final[dfp_final["STATUS_NORM"].str.contains("ANALISE|PENDEN")]

for i, (nome, termo) in enumerate(origens_map.items()):
    qtd = df_ativas["ORIGEM_NORM"].str.contains(termo).sum()
    cols_o[i].metric(nome, int(qtd))

# =========================================================
# GRÁFICOS E TABELAS
# =========================================================
st.markdown("---")
st.subheader("📈 Evolução diária")
chart = alt.Chart(df).mark_line().encode(x="DATA:T", y="TOTAL:Q", color=alt.value("#3b82f6"))
st.altair_chart(chart, use_container_width=True)

st.subheader("📋 Detalhe Processos")
st.dataframe(dfp_final[["DATA", "CHAVE_CLIENTE", "SITUAÇÃO", "ORIGEM"]], use_container_width=True)