import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import date, datetime, timedelta

from app_dashboard import carregar_dados_planilha
from utils.supremo_config import TOKEN_SUPREMO

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Corretores – Visão Geral",
    page_icon="🧑‍💼",
    layout="wide",
)

# ---------------------------------------------------------
# CARREGAMENTO DE DADOS
# ---------------------------------------------------------
df_planilha = carregar_dados_planilha()

if df_planilha is None or df_planilha.empty:
    st.error("Não foi possível carregar os dados da planilha principal.")
    st.stop()

df_planilha = df_planilha.copy()

# Normalização de datas
if "DIA" in df_planilha.columns:
    df_planilha["DIA"] = pd.to_datetime(df_planilha["DIA"], errors="coerce")
elif "DATA" in df_planilha.columns:
    df_planilha["DIA"] = pd.to_datetime(df_planilha["DATA"], errors="coerce")
else:
    df_planilha["DIA"] = pd.NaT

# Normalização de Corretor / Equipe
df_planilha["CORRETOR_NORM"] = (
    df_planilha.get("CORRETOR", "NÃO INFORMADO")
    .fillna("NÃO INFORMADO")
    .astype(str)
    .str.upper()
    .str.strip()
)
df_planilha["EQUIPE_NORM"] = (
    df_planilha.get("EQUIPE", "SEM EQUIPE")
    .fillna("SEM EQUIPE")
    .astype(str)
    .str.upper()
    .str.strip()
)

# Status Base
if "STATUS_BASE" in df_planilha.columns:
    df_planilha["STATUS_BASE_NORM"] = (
        df_planilha["STATUS_BASE"].fillna("").astype(str).str.upper().str.strip()
    )
else:
    df_planilha["STATUS_BASE_NORM"] = ""

# VGV
if "VGV" not in df_planilha.columns:
    df_planilha["VGV"] = 0.0
else:
    df_planilha["VGV"] = pd.to_numeric(df_planilha["VGV"], errors="coerce").fillna(0.0)

# CSS
st.markdown("""
<style>
.top-banner {
    background: linear-gradient(90deg, #111827, #1f2937);
    padding: 1.2rem 1.5rem;
    border-radius: 1rem;
    border: 1px solid #374151;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1rem;
}
.top-banner-title {
    font-size: 1.4rem;
    font-weight: 700;
    color: #f9fafb;
}
.top-banner-subtitle {
    font-size: 0.85rem;
    color: #d1d5db;
    margin-top: 0.2rem;
}
.motivational-text {
    font-size: 0.85rem;
    color: #e5e7eb;
    margin-bottom: 1.2rem;
}
.metric-card {
    background: #111827;
    border-radius: 0.9rem;
    padding: 0.9rem 1.1rem;
    border: 1px solid #1f2937;
    box-shadow: 0 10px 25px rgba(15,23,42,0.45);
}
.metric-value {
    font-size: 1.6rem;
    font-weight: 700;
    color: #f9fafb;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# BUSCAR CORRETORES DO CRM
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def buscar_corretores():
    try:
        resp = requests.get(
            "https://api.supremocrm.com.br/v1/corretores",
            headers={"Authorization": f"Bearer {TOKEN_SUPREMO}"},
            timeout=20
        )
        if resp.status_code != 200:
            return pd.DataFrame()

        data = resp.json().get("data", [])
        df = pd.DataFrame(data)

        df["NOME_CRM"] = df["nome"].astype(str).str.upper().str.strip()
        df["ATIVO_CRM"] = df["status"].astype(str).str.upper().str.strip() == "ATIVO"
        return df

    except:
        return pd.DataFrame()

df_corretores_crm = buscar_corretores()

# ---------------------------------------------------------
# FILTROS LATERAIS
# ---------------------------------------------------------
hoje = date.today()
data_ini_padrao = hoje - timedelta(days=60)

with st.sidebar:
    st.markdown("### Filtros – Corretores")

    data_ini = st.date_input("Data inicial", data_ini_padrao)
    data_fim = st.date_input("Data final", hoje)

    equipe_sel = st.selectbox(
        "Filtrar equipe",
        ["TODAS"] + sorted(df_planilha["EQUIPE_NORM"].unique())
    )

    corretor_sel = st.selectbox(
        "Filtrar corretor",
        ["TODOS"] + sorted(df_planilha["CORRETOR_NORM"].unique())
    )

    opcao_tipo_venda = st.radio(
        "Tipo de venda considerada",
        ["VENDA GERADA + INFORMADA", "Só VENDA GERADA", "Só VENDA INFORMADA"]
    )

# ---------------------------------------------------------
# MAPEAMENTO DO FILTRO DE TIPO DE VENDA
# ---------------------------------------------------------
if opcao_tipo_venda == "Só VENDA GERADA":
    status_vendas_considerados = ["VENDA GERADA"]

elif opcao_tipo_venda == "Só VENDA INFORMADA":
    status_vendas_considerados = ["VENDA INFORMADA"]

else:
    status_vendas_considerados = ["VENDA GERADA", "VENDA INFORMADA"]

# ---------------------------------------------------------
# FILTRO DE PERÍODO
# ---------------------------------------------------------
mask_periodo = (
    (df_planilha["DIA"].dt.date >= data_ini) &
    (df_planilha["DIA"].dt.date <= data_fim)
)

df_plan_periodo = df_planilha.loc[mask_periodo].copy()

if equipe_sel != "TODAS":
    df_plan_periodo = df_plan_periodo[
        df_plan_periodo["EQUIPE_NORM"] == equipe_sel
    ]

if corretor_sel != "TODOS":
    df_plan_periodo = df_plan_periodo[
        df_plan_periodo["CORRETOR_NORM"] == corretor_sel
    ]

# ---------------------------------------------------------
# TRECHO CORRIGIDO – SEM ERRO .dt
# ---------------------------------------------------------
df_ult_mov = (
    df_planilha.groupby("CORRETOR_NORM")["DIA"]
    .max()
    .reset_index()
    .rename(columns={"DIA": "ULTIMA_DATA"})
)

df_ult_mov["ULTIMA_DATA"] = pd.to_datetime(df_ult_mov["ULTIMA_DATA"], errors="coerce")

df_ult_mov["ULTIMA_DATA"].fillna(pd.Timestamp("1900-01-01"), inplace=True)

df_ult_mov["ULTIMA_DATA_DATE"] = df_ult_mov["ULTIMA_DATA"].dt.date

df_ult_mov["DIAS_SEM_MOV"] = (date.today() - df_ult_mov["ULTIMA_DATA_DATE"]).dt.days

# ---------------------------------------------------------
# CÁLCULO DE INDICADORES
# ---------------------------------------------------------
df_plan_periodo["IS_ANALISE"] = df_plan_periodo["STATUS_BASE_NORM"].isin(["EM ANÁLISE", "REANÁLISE"])
df_plan_periodo["IS_APROV"] = df_plan_periodo["STATUS_BASE_NORM"].str.contains("APROV", na=False)

df_plan_periodo["IS_VENDA"] = df_plan_periodo["STATUS_BASE_NORM"].isin(status_vendas_considerados)

df_plan_periodo["VGV_VENDA"] = np.where(df_plan_periodo["IS_VENDA"], df_plan_periodo["VGV"], 0)

total_analises = int(df_plan_periodo["IS_ANALISE"].sum())
total_aprov = int(df_plan_periodo["IS_APROV"].sum())
total_vendas = int(df_plan_periodo["IS_VENDA"].sum())
total_vgv = float(df_plan_periodo["VGV_VENDA"].sum())

# ---------------------------------------------------------
# CABEÇALHO
# ---------------------------------------------------------
col1, col2 = st.columns([3,1])

with col1:
    st.markdown(f"""
    <div class="top-banner">
        <div>
            <div class="top-banner-title">🧑‍💼 Corretores – Visão Geral</div>
            <p class="top-banner-subtitle">
                Período analisado: <strong>{data_ini.strftime('%d/%m/%Y')}</strong> a 
                <strong>{data_fim.strftime('%d/%m/%Y')}</strong><br>
                Vendas consideradas: <strong>{opcao_tipo_venda}</strong>
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    try:
        st.image("logo_mr.png", use_container_width=True)
    except:
        pass

# ---------------------------------------------------------
# TABELA FINAL – PAINEL
# ---------------------------------------------------------
df_rank = (
    df_plan_periodo.groupby(["CORRETOR_NORM", "EQUIPE_NORM"])
    .agg(
        ANALISES=("IS_ANALISE", "sum"),
        APROVACAO=("IS_APROV", "sum"),
        VENDAS=("IS_VENDA", "sum"),
        VGV=("VGV_VENDA", "sum")
    )
    .reset_index()
)

df_rank = df_rank.merge(df_ult_mov[["CORRETOR_NORM", "DIAS_SEM_MOV"]], on="CORRETOR_NORM", how="left")

df_rank = df_rank.sort_values(by=["EQUIPE_NORM", "VGV"], ascending=[True, False])

st.markdown("### 📊 Painel de Corretores")

st.dataframe(
    df_rank.style.format({
        "VGV": "R$ {:,.0f}".format
    }),
    use_container_width=True,
    hide_index=True
)
