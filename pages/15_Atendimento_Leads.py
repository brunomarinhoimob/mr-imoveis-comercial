import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Controle de Atendimento de Leads",
    page_icon="📞",
    layout="wide",
)

st.sidebar.image("logo_mr.png", use_column_width=True)

st.title("📞 Controle de Atendimento de Leads")
st.caption("Visão simples do atendimento: leads atendidos, não atendidos, tempo e leads novos.")

# ---------------------------------------------------------
# CARREGANDO DF DE LEADS
# ---------------------------------------------------------
if "df_leads" not in st.session_state or st.session_state["df_leads"] is None:
    st.error("Nenhum dado carregado. Volte para a tela inicial.")
    st.stop()

df_raw = st.session_state["df_leads"].copy()

# ---------------------------------------------------------
# FUNÇÃO DE BUSCA INTELIGENTE DE COLUNAS
# ---------------------------------------------------------
def get_col(possiveis_nomes):
    cols_lower = {c.lower(): c for c in df_raw.columns}
    for nome in possiveis_nomes:
        nome_lower = nome.lower()
        for base, real in cols_lower.items():
            if nome_lower in base:
                return real
    return None

# ---------------------------------------------------------
# NORMALIZAÇÃO DAS COLUNAS
# ---------------------------------------------------------
df = df_raw.copy()

# Nome lead
col_nome_lead = get_col(["nome_pessoa", "nome", "lead"])
df["NOME_LEAD"] = df[col_nome_lead].astype(str) if col_nome_lead else ""

# Telefone
col_tel = get_col(["telefone", "telefone_pessoa", "whatsapp"])
df["TELEFONE_LEAD"] = df[col_tel].astype(str) if col_tel else ""

# Corretor ---------- CORREÇÃO AQUI 🔥
col_corretor = get_col([
    "nome_corretor",     # nome exato da API
    "corretor",
    "responsavel",
    "responsável",
    "consultor",
    "usuario",
    "usuário"
])

if col_corretor:
    df["CORRETOR_EXIBICAO"] = df[col_corretor].fillna("").astype(str)
else:
    df["CORRETOR_EXIBICAO"] = ""

df["Corretor responsável"] = df["CORRETOR_EXIBICAO"]

# Situação
col_situacao = get_col(["nome_situacao", "situacao", "situação"])

# Etapa
col_etapa = get_col(["status", "etapa", "fase"])

# Datas
col_data_captura = get_col(["data_captura"])
df["DATA_CAPTURA_DT"] = pd.to_datetime(df[col_data_captura], errors="coerce") if col_data_captura else pd.NaT

col_data_primeiro = get_col(["data_com_corretor", "data_qualificando"])
df["DATA_COM_CORRETOR_DT"] = pd.to_datetime(df[col_data_primeiro], errors="coerce") if col_data_primeiro else pd.NaT

col_data_ultima = get_col(["data_ultima_interacao"])
df["DATA_ULT_INTERACAO_DT"] = pd.to_datetime(df[col_data_ultima], errors="coerce") if col_data_ultima else pd.NaT

# Perdido
df["PERDIDO"] = False
if col_situacao:
    df["PERDIDO"] = df[col_situacao].astype(str).str.upper().str.contains("PERD")

# Atendido
df["ATENDIDO"] = df["DATA_COM_CORRETOR_DT"].notna()

# Tempo atendimento
df["TEMPO_ATEND_MIN"] = (
    (df["DATA_COM_CORRETOR_DT"] - df["DATA_CAPTURA_DT"]).dt.total_seconds() / 60
)

# Tempo interações
df["TEMPO_INTERACOES_MIN"] = (
    (df["DATA_ULT_INTERACAO_DT"] - df["DATA_COM_CORRETOR_DT"]).dt.total_seconds() / 60
)

def fmt_dt(dt):
    return "" if pd.isna(dt) else dt.strftime("%d/%m/%Y %H:%M")

def fmt_min(x):
    if pd.isna(x): return "-"
    x = int(x)
    return f"{x//60}h {x%60}min" if x >= 60 else f"{x} min"

# ---------------------------------------------------------
# FILTROS
# ---------------------------------------------------------
st.sidebar.header("Filtros")

data_min = df["DATA_CAPTURA_DT"].min()
data_max = df["DATA_CAPTURA_DT"].max()

data_ini = st.sidebar.date_input("Data inicial", value=data_max.date() - timedelta(days=7))
data_fim = st.sidebar.date_input("Data final", value=data_max.date())

mask = (df["DATA_CAPTURA_DT"].dt.date >= data_ini) & (df["DATA_CAPTURA_DT"].dt.date <= data_fim)
df_periodo = df[mask].copy()

# filtro corretor
corretores = sorted(df_periodo["Corretor responsável"].unique().tolist())
sel = st.sidebar.selectbox("Corretor", ["Todos"] + corretores)

if sel != "Todos":
    df_periodo = df_periodo[df_periodo["Corretor responsável"] == sel]

if df_periodo.empty:
    st.warning("Nenhum lead encontrado no período.")
    st.stop()

# ---------------------------------------------------------
# KPIs
# ---------------------------------------------------------
leads = len(df_periodo)
atendidos = df_periodo["ATENDIDO"].sum()
nao_atendidos = leads - atendidos
perdidos = df_periodo["PERDIDO"].sum()

tempo_med = df_periodo.loc[df_periodo["ATENDIDO"], "TEMPO_ATEND_MIN"].mean()

# leads novos
df_novos = df_periodo[(~df_periodo["ATENDIDO"]) & (~df_periodo["PERDIDO"])]
qtd_novos = len(df_novos)

# % até 15 minutos
pct_15 = (df_periodo["TEMPO_ATEND_MIN"] <= 15).sum() / atendidos * 100 if atendidos else 0

# cards
c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
c1.metric("Leads no período", leads)
c2.metric("Atendidos", atendidos)
c3.metric("Não atendidos", nao_atendidos)
c4.metric("Perdidos", perdidos)
c5.metric("Tempo médio atendimento", fmt_min(tempo_med) if not pd.isna(tempo_med) else "-")
c6.metric("Leads novos", qtd_novos)
c7.metric("% até 15 min", f"{pct_15:.1f}%")

# ---------------------------------------------------------
# LEADS NOVOS
# ---------------------------------------------------------
st.markdown("### 📥 Leads novos (não atendidos + não perdidos)")
if qtd_novos == 0:
    st.info("Nenhum lead novo encontrado.")
else:
    df_temp = df_novos.copy()
    df_temp["Captura"] = df_temp["DATA_CAPTURA_DT"].apply(fmt_dt)
    st.dataframe(df_temp[["NOME_LEAD", "TELEFONE_LEAD", "Corretor responsável", "Captura"]])

# ---------------------------------------------------------
# RESUMO POR CORRETOR
# ---------------------------------------------------------
st.markdown("## 👥 Resumo geral por corretor")

agr = df_periodo.groupby("Corretor responsável").agg(
    LEADS=("NOME_LEAD", "count"),
    ATENDIDOS=("ATENDIDO", "sum"),
    TM_ATEND_MIN=("TEMPO_ATEND_MIN", "mean"),
    TM_INTERACOES_MIN=("TEMPO_INTERACOES_MIN", "mean")
).reset_index()

agr["Tempo atendimento"] = agr["TM_ATEND_MIN"].apply(fmt_min)
agr["Tempo interações"] = agr["TM_INTERACOES_MIN"].apply(fmt_min)

st.dataframe(
    agr[["Corretor responsável", "LEADS", "ATENDIDOS", "Tempo atendimento", "Tempo interações"]],
    use_container_width=True
)

# ---------------------------------------------------------
# DETALHAMENTO
# ---------------------------------------------------------
st.markdown("## 📂 Detalhamento dos leads")

aba1, aba2, aba3 = st.tabs(["Atendidos", "Não atendidos", "Apenas 1 contato"])

# --- Atendidos
with aba1:
    df_at = df_periodo[df_periodo["ATENDIDO"] & (~df_periodo["PERDIDO"])].copy()
    if df_at.empty:
        st.info("Nenhum lead atendido.")
    else:
        df_at["Captura"] = df_at["DATA_CAPTURA_DT"].apply(fmt_dt)
        df_at["1º contato"] = df_at["DATA_COM_CORRETOR_DT"].apply(fmt_dt)
        df_at["Última interação"] = df_at["DATA_ULT_INTERACAO_DT"].apply(fmt_dt)
        df_at["Tempo atendimento"] = df_at["TEMPO_ATEND_MIN"].apply(fmt_min)

        cols = ["NOME_LEAD", "TELEFONE_LEAD", "Corretor responsável", "Captura", "1º contato", "Última interação", "Tempo atendimento"]
        st.dataframe(df_at[cols], use_container_width=True)

# --- Não atendidos
with aba2:
    df_na = df_periodo[(~df_periodo["ATENDIDO"]) & (~df_periodo["PERDIDO"])].copy()
    if df_na.empty:
        st.info("Nenhum lead não atendido.")
    else:
        df_na["Captura"] = df_na["DATA_CAPTURA_DT"].apply(fmt_dt)
        st.dataframe(df_na[["NOME_LEAD", "TELEFONE_LEAD", "Corretor responsável", "Captura"]], use_container_width=True)

# --- Apenas 1 contato
with aba3:
    df_1 = df_periodo[
        (df_periodo["ATENDIDO"]) &
        (df_periodo["DATA_ULT_INTERACAO_DT"].isna()) &
        (~df_periodo["PERDIDO"])
    ].copy()

    if df_1.empty:
        st.info("Nenhum lead com apenas 1 contato.")
    else:
        df_1["Captura"] = df_1["DATA_CAPTURA_DT"].apply(fmt_dt)
        df_1["1º contato"] = df_1["DATA_COM_CORRETOR_DT"].apply(fmt_dt)
        st.dataframe(df_1[["NOME_LEAD", "TELEFONE_LEAD", "Corretor responsável", "Captura", "1º contato"]], use_container_width=True)
