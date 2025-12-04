import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import date
from app_dashboard import carregar_dados_planilha


# ---------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------
def mes_ano_ptbr_para_date(texto: str):
    """Converte 'novembro 2025' -> date(2025, 11, 1)."""
    if not isinstance(texto, str):
        return pd.NaT
    t = texto.strip().lower()
    partes = t.split()
    if len(partes) != 2:
        return pd.NaT
    mes_nome, ano_str = partes
    mapa = {
        "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3,
        "abril": 4, "maio": 5, "junho": 6, "julho": 7,
        "agosto": 8, "setembro": 9, "outubro": 10,
        "novembro": 11, "dezembro": 12,
    }
    mes = mapa.get(mes_nome)
    if not mes:
        return pd.NaT
    try:
        return date(int(ano_str), mes, 1)
    except:
        return pd.NaT


def conta_analises_base(s): return (s == "EM ANÁLISE").sum()
def conta_reanalises(s): return (s == "REANÁLISE").sum()
def conta_aprovacoes(s): return (s == "APROVADO").sum()


def obter_vendas_unicas(df_scope, status_venda=None):
    if df_scope.empty:
        return df_scope.copy()

    if status_venda is None:
        status_venda = ["VENDA GERADA", "VENDA INFORMADA"]

    df2 = df_scope[df_scope["STATUS_BASE"].isin(status_venda)].copy()
    if df2.empty:
        return df2

    if "NOME_CLIENTE_BASE" not in df2.columns:
        df2["NOME_CLIENTE_BASE"] = df2["CLIENTE"].fillna("").astype(str).str.upper().str.strip()
    if "CPF_CLIENTE_BASE" not in df2.columns:
        df2["CPF_CLIENTE_BASE"] = ""

    df2["CHAVE_CLIENTE"] = (
        df2["NOME_CLIENTE_BASE"].astype(str).str.upper().str.strip()
        + " | "
        + df2["CPF_CLIENTE_BASE"].astype(str).str.strip()
    )

    df2 = df2.sort_values("DIA")
    return df2.groupby("CHAVE_CLIENTE").tail(1).copy()


def format_currency(v):
    try:
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"


# ---------------------------------------------------------
# CONFIG DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Funil do Corretor",
    page_icon="🧑‍💼",
    layout="wide",
)

st.title("🧑‍💼 Funil Individual do Corretor")
st.caption("Análises, aprovações, vendas, meta e acompanhamento por período + DATA BASE.")


# ---------------------------------------------------------
# CARREGA BASE
# ---------------------------------------------------------
df = carregar_dados_planilha()
if df.empty:
    st.error("Erro ao carregar planilha.")
    st.stop()

df["DIA"] = pd.to_datetime(df["DIA"], errors="coerce")

# DATA BASE
if "DATA BASE" in df.columns:
    df["DATA_BASE"] = df["DATA BASE"].astype(str).apply(mes_ano_ptbr_para_date)
    df["DATA_BASE_LABEL"] = df["DATA_BASE"].apply(lambda d: d.strftime("%m/%Y") if pd.notnull(d) else "")
else:
    df["DATA_BASE"] = df["DIA"]
    df["DATA_BASE_LABEL"] = df["DIA"].dt.strftime("%m/%Y")

# Lista corretores
corretores = sorted(df["CORRETOR"].dropna().astype(str).unique())

corretor_sel = st.sidebar.selectbox("Selecione o corretor", corretores)

df_cor = df[df["CORRETOR"] == corretor_sel].copy()
if df_cor.empty:
    st.warning("Nenhum dado do corretor.")
    st.stop()

# ---------------------------------------------------------
# SELECTOR DATA BASE
# ---------------------------------------------------------
bases_validas = (
    df_cor[["DATA_BASE", "DATA_BASE_LABEL"]]
    .dropna(subset=["DATA_BASE"])
    .drop_duplicates()
    .sort_values("DATA_BASE")
)

opcoes_bases = bases_validas["DATA_BASE_LABEL"].tolist()
default_bases = opcoes_bases[-2:] if len(opcoes_bases) >= 2 else opcoes_bases

bases_selecionadas = st.sidebar.multiselect(
    "DATA BASE do corretor",
    options=opcoes_bases,
    default=default_bases
)

if not bases_selecionadas:
    bases_selecionadas = opcoes_bases

df_periodo = df_cor[df_cor["DATA_BASE_LABEL"].isin(bases_selecionadas)].copy()
if df_periodo.empty:
    st.warning("Nenhum registro do corretor no período.")
    st.stop()

# Tipo de venda
radio_venda = st.sidebar.radio(
    "Tipo de venda",
    ("VENDA GERADA + INFORMADA", "Só VENDA GERADA")
)
status_venda_considerado = ["VENDA GERADA"] if radio_venda == "Só VENDA GERADA" else ["VENDA GERADA", "VENDA INFORMADA"]


# ---------------------------------------------------------
# INTERVALO REAL PELOS DIAS DA PLANILHA
# ---------------------------------------------------------
dias_validos = df_periodo["DIA"].dropna()

if len(dias_validos) > 0:
    data_ini_mov = dias_validos.min().date()
    data_fim_mov = dias_validos.max().date()
else:
    hoje = date.today()
    data_ini_mov, data_fim_mov = hoje, hoje

if len(bases_selecionadas) == 1:
    base_txt = bases_selecionadas[0]
else:
    base_txt = f"{bases_selecionadas[0]} até {bases_selecionadas[-1]}"

st.caption(
    f"Corretor: **{corretor_sel}** • DATA BASE: **{base_txt}** • "
    f"Dias: **{data_ini_mov.strftime('%d/%m/%Y')}** → **{data_fim_mov.strftime('%d/%m/%Y')}**"
)


# ---------------------------------------------------------
# KPIs DO CORRETOR
# ---------------------------------------------------------
st.markdown("## 📌 Funil do período (corretor)")

status = df_periodo["STATUS_BASE"].fillna("").astype(str).str.upper()

analises_em = conta_analises_base(status)
reanalises = conta_reanalises(status)
aprovacoes = conta_aprovacoes(status)

df_vendas = obter_vendas_unicas(df_periodo, status_vendas=status_venda_considerado)
vendas = len(df_vendas)
vgv = df_vendas["VGV"].sum() if not df_vendas.empty else 0

# EXIBE KPIs
col1, col2, col3 = st.columns(3)
col1.metric("Análises (EM)", analises_em)
col2.metric("Aprovações", aprovacoes)
col3.metric("Vendas", vendas)

col4, col5 = st.columns(2)
col4.metric("Reanálises", reanalises)
col5.metric("VGV total", format_currency(vgv))

st.markdown("---")


# ---------------------------------------------------------
# PLANEJAMENTO (META)
# ---------------------------------------------------------
st.markdown("## 🎯 Planejamento baseado no funil do corretor")

if vendas > 0:
    analises_por_venda = analises_em / vendas if analises_em > 0 else 0
    aprovacoes_por_venda = aprovacoes / vendas if aprovacoes > 0 else 0

    meta_vendas = st.number_input(
        "Meta de vendas do corretor",
        min_value=0,
        step=1,
        value=vendas
    )

    if meta_vendas > 0:
        analises_necessarias = int(np.ceil(analises_por_venda * meta_vendas))
        aprovacoes_necessarias = int(np.ceil(aprovacoes_por_venda * meta_vendas))

        c1, c2, c3 = st.columns(3)
        c1.metric("Meta de vendas", meta_vendas)
        c2.metric("Análises necessárias", analises_necessarias)
        c3.metric("Aprovações necessárias", aprovacoes_necessarias)

        st.caption("Valores calculados com base no funil REAL do corretor no período.")

        # ---------------------------------------------------------
        # 📊 GRÁFICO META x REAL (INDICADOR INDIVIDUAL)
        # ---------------------------------------------------------
        st.markdown("### 📊 Acompanhamento da meta – corretor")

        indicador = st.selectbox("Indicador", ["Análises", "Aprovações", "Vendas"])

        periodo_acomp = st.date_input(
            "Período do acompanhamento",
            value=(data_ini_mov, data_fim_mov)
        )

        data_ini_sel, data_fim_sel = periodo_acomp

        dr = pd.date_range(start=data_ini_sel, end=data_fim_sel)
        dias_meta = [d.date() for d in dr]

        df_periodo["DIA_DATA"] = df_periodo["DIA"].dt.date

        # Filtra somente dentro do período do gráfico
        df_range = df_periodo[
            (df_periodo["DIA_DATA"] >= data_ini_sel)
            & (df_periodo["DIA_DATA"] <= data_fim_sel)
        ]

        if indicador == "Análises":
            df_temp = df_range[df_range["STATUS_BASE"] == "EM ANÁLISE"]
            total_meta = analises_necessarias
        elif indicador == "Aprovações":
            df_temp = df_range[df_range["STATUS_BASE"] == "APROVADO"]
            total_meta = aprovacoes_necessarias
        else:
            df_temp = obter_vendas_unicas(df_range, status_venda_considerado)
            total_meta = meta_vendas

        # Cálculo de acumulado REAL
        cont_por_dia = (
            df_temp.groupby("DIA_DATA")
            .size()
            .reindex(dias_meta, fill_value=0)
        )

        df_line = pd.DataFrame({
            "DIA": pd.to_datetime(dias_meta),
            "Real": np.cumsum(cont_por_dia.values)
        })

        # Linha Real PARA no último dia com movimento
        if not df_temp.empty:
            ultimo_mov = df_temp["DIA_DATA"].max()
            df_line.loc[df_line["DIA"].dt.date > ultimo_mov, "Real"] = np.nan

        # Linha Meta linear
        df_line["Meta"] = np.linspace(0, total_meta, len(df_line))

        df_plot = df_line.melt("DIA", var_name="Série", value_name="Valor")

        chart = (
            alt.Chart(df_plot)
            .mark_line(point=True)
            .encode(
                x=alt.X("DIA:T", title="Dia"),
                y=alt.Y("Valor:Q", title="Quantidade acumulada"),
                color=alt.Color("Série:N", title=""),
            )
            .properties(height=350)
        )

        st.altair_chart(chart, use_container_width=True)

else:
    st.info("Corretor sem vendas no período — não é possível projetar meta.")


