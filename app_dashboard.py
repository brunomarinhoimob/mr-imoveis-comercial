import streamlit as st
import pandas as pd
import numpy as np
from datetime import date

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Imobiliária – MR Imóveis",
    page_icon="🏠",
    layout="wide",
)

# ---------------------------------------------------------
# ESTILO (CSS)
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp {
        background-color: #050814;
        color: #f5f5f5;
    }
    section[data-testid="stSidebar"] {
        background: #111827;
        border-right: 1px solid #1f2937;
    }
    div[data-testid="stMetric"] {
        background: #111827;
        padding: 16px;
        border-radius: 16px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.45);
        border: 1px solid #1f2937;
    }
    .dataframe tbody tr:hover {
        background: #111827 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# LOGO MR IMÓVEIS (coloque logo_mr.png na mesma pasta)
# ---------------------------------------------------------
LOGO_PATH = "logo_mr.png"
try:
    st.sidebar.image(LOGO_PATH, use_container_width=True)
except Exception:
    st.sidebar.write("MR Imóveis")

# ---------------------------------------------------------
# CONFIG: LINK DA PLANILHA
# ---------------------------------------------------------
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID_ANALISES = "1574157905"

CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ANALISES}"

# ---------------------------------------------------------
# FUNÇÃO AUXILIAR PARA LIMPAR DATA
# ---------------------------------------------------------
def limpar_para_data(serie):
    dt = pd.to_datetime(serie, dayfirst=True, errors="coerce")
    return dt.dt.date

# ---------------------------------------------------------
# CARREGAR DADOS
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def carregar_dados():
    df = pd.read_csv(CSV_URL)

    # Padroniza colunas
    df.columns = [c.strip().upper() for c in df.columns]

    # DATA / DIA
    if "DATA" in df.columns:
        df["DIA"] = limpar_para_data(df["DATA"])
    elif "DIA" in df.columns:
        df["DIA"] = limpar_para_data(df["DIA"])
    else:
        df["DIA"] = pd.NaT

    # EQUIPE / CORRETOR
    for col in ["EQUIPE", "CORRETOR"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .fillna("NÃO INFORMADO")
                .astype(str)
                .str.upper()
                .str.strip()
            )
        else:
            df[col] = "NÃO INFORMADO"

    # SITUAÇÃO BASE
    possiveis_cols_situacao = [
        "SITUAÇÃO",
        "SITUAÇÃO ATUAL",
        "STATUS",
        "SITUACAO",
        "SITUACAO ATUAL",
    ]
    col_situacao = None
    for c in possiveis_cols_situacao:
        if c in df.columns:
            col_situacao = c
            break

    df["STATUS_BASE"] = ""
    if col_situacao:
        status = df[col_situacao].fillna("").astype(str).str.upper()

        df.loc[status.str.contains("EM ANÁLISE"), "STATUS_BASE"] = "EM ANÁLISE"
        df.loc[status.str.contains("REANÁLISE"), "STATUS_BASE"] = "REANÁLISE"
        df.loc[status.str.contains("APROV"), "STATUS_BASE"] = "APROVADO"
        df.loc[status.str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
        df.loc[status.str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA GERADA"
        df.loc[status.str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA INFORMADA"

    # VGV (via coluna OBSERVAÇÕES) – sempre em REAL
    if "OBSERVAÇÕES" in df.columns:
        df["VGV"] = pd.to_numeric(df["OBSERVAÇÕES"], errors="coerce").fillna(0.0)
    else:
        df["VGV"] = 0.0

    return df


df = carregar_dados()

if df.empty:
    st.error("Não foi possível carregar dados da planilha. Verifique o link/gid.")
    st.stop()

# ---------------------------------------------------------
# SIDEBAR - FILTROS
# ---------------------------------------------------------
st.sidebar.title("Filtros 🔎")

dias_validos = pd.Series(df["DIA"].dropna())

if not dias_validos.empty:
    data_min = dias_validos.min()
    data_max = dias_validos.max()
else:
    hoje = date.today()
    data_min = hoje
    data_max = hoje

periodo = st.sidebar.date_input(
    "Período",
    value=(data_min, data_max),
    min_value=data_min,
    max_value=data_max,
)

if isinstance(periodo, tuple):
    data_ini, data_fim = periodo
else:
    data_ini, data_fim = data_min, data_max

# Filtro de equipe
lista_equipes = sorted(df["EQUIPE"].dropna().unique())
equipe_sel = st.sidebar.selectbox("Equipe", ["Todas"] + lista_equipes)

# Base para montar lista de corretores (dependente da equipe)
if equipe_sel == "Todas":
    base_cor = df
else:
    base_cor = df[df["EQUIPE"] == equipe_sel]

lista_corretor = sorted(base_cor["CORRETOR"].dropna().unique())
corretor_sel = st.sidebar.selectbox("Corretor", ["Todos"] + lista_corretor)

# ---------------------------------------------------------
# APLICA OS FILTROS
# ---------------------------------------------------------
df_filtrado = df.copy()

# Período
dia_series_all = limpar_para_data(df_filtrado["DIA"])
mask_data_all = (dia_series_all >= data_ini) & (dia_series_all <= data_fim)
df_filtrado = df_filtrado[mask_data_all]

# Equipe
if equipe_sel != "Todas":
    df_filtrado = df_filtrado[df_filtrado["EQUIPE"] == equipe_sel]

# Corretor
if corretor_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["CORRETOR"] == corretor_sel]

registros_filtrados = len(df_filtrado)

# ---------------------------------------------------------
# TÍTULO / CABEÇALHO
# ---------------------------------------------------------
st.title("📊 Dashboard Imobiliária – MR Imóveis")
caption_text = (
    f"Período: **{data_ini.strftime('%d/%m/%Y')}** até **{data_fim.strftime('%d/%m/%Y')}** • "
    f"Registros filtrados: **{registros_filtrados}**"
)

if equipe_sel != "Todas":
    caption_text += f" • Equipe: **{equipe_sel}**"
if corretor_sel != "Todos":
    caption_text += f" • Corretor: **{corretor_sel}**"

st.caption(caption_text)

if df_filtrado.empty:
    st.warning("Não há registros para os filtros selecionados.")
    st.stop()

# ---------------------------------------------------------
# CÁLCULOS PRINCIPAIS
# ---------------------------------------------------------
em_analise = (df_filtrado["STATUS_BASE"] == "EM ANÁLISE").sum()
reanalise = (df_filtrado["STATUS_BASE"] == "REANÁLISE").sum()
aprovacoes = (df_filtrado["STATUS_BASE"] == "APROVADO").sum()
reprovacoes = (df_filtrado["STATUS_BASE"] == "REPROVADO").sum()
venda_gerada = (df_filtrado["STATUS_BASE"] == "VENDA GERADA").sum()
venda_informada = (df_filtrado["STATUS_BASE"] == "VENDA INFORMADA").sum()

analises_total = em_analise + reanalise
vendas_total = venda_gerada + venda_informada

taxa_aprov_analise = (aprovacoes / analises_total * 100) if analises_total > 0 else 0
taxa_venda_analise = (vendas_total / analises_total * 100) if analises_total > 0 else 0
taxa_venda_aprov = (vendas_total / aprovacoes * 100) if aprovacoes > 0 else 0

vgv_total = df_filtrado["VGV"].sum()
maior_vgv = df_filtrado["VGV"].max() if registros_filtrados > 0 else 0
ticket_medio = (vgv_total / vendas_total) if vendas_total > 0 else 0

# ---------------------------------------------------------
# VISÃO GERAL – MÉTRICAS
# ---------------------------------------------------------
st.subheader("Resumo de Análises, Aprovações e Vendas")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Em análise", em_analise)
with c2:
    st.metric("Reanálise", reanalise)
with c3:
    st.metric("Aprovações (Total)", aprovacoes)
with c4:
    st.metric("Reprovações", reprovacoes)

c5, c6, c7 = st.columns(3)
with c5:
    st.metric("Vendas GERADAS", venda_gerada)
with c6:
    st.metric("Vendas INFORMADAS", venda_informada)
with c7:
    st.metric("Vendas (Total)", vendas_total)

c8, c9, c10 = st.columns(3)
with c8:
    st.metric("Taxa aprovações / análises", f"{taxa_aprov_analise:.1f}%")
with c9:
    st.metric("Taxa vendas / análises", f"{taxa_venda_analise:.1f}%")
with c10:
    st.metric("Taxa vendas / aprovações", f"{taxa_venda_aprov:.1f}%")

st.markdown("---")
st.subheader("💰 Indicadores de VGV")

c11, c12, c13 = st.columns(3)
with c11:
    st.metric(
        "VGV Total (filtrado)",
        f"R$ {vgv_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
    )
with c12:
    st.metric(
        "Ticket Médio por venda",
        f"R$ {ticket_medio:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
    )
with c13:
    st.metric(
        "Maior VGV em uma venda",
        f"R$ {maior_vgv:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
    )

st.markdown(
    "<hr style='border-color:#1f2937'>"
    "<p style='text-align:center; color:#6b7280;'>"
    "Dashboard MR Imóveis conectado ao Google Sheets. "
    "Atualize a planilha e, em até 1 minuto, o painel é recarregado automaticamente."
    "</p>",
    unsafe_allow_html=True,
)
