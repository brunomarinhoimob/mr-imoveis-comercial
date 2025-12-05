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
        "janeiro": 1,
        "fevereiro": 2,
        "março": 3,
        "marco": 3,
        "abril": 4,
        "maio": 5,
        "junho": 6,
        "julho": 7,
        "agosto": 8,
        "setembro": 9,
        "outubro": 10,
        "novembro": 11,
        "dezembro": 12,
    }
    mes = mapa.get(mes_nome)
    if not mes:
        return pd.NaT
    try:
        return date(int(ano_str), mes, 1)
    except Exception:
        return pd.NaT


def conta_analises_base(s: pd.Series) -> int:
    return (s == "EM ANÁLISE").sum()


def conta_reanalises(s: pd.Series) -> int:
    return (s == "REANÁLISE").sum()


def conta_aprovacoes(s: pd.Series) -> int:
    return (s == "APROVADO").sum()


def format_currency(v) -> str:
    try:
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


# ---------------------------------------------------------
# 🔥 FUNÇÃO DE VENDAS COM REGRA DO DESISTIU
# ---------------------------------------------------------
def obter_vendas_unicas(df_scope, status_venda=None, status_final_map=None):
    """
    Retorna 1 venda por cliente (último status de venda).
    Aplica a regra do DESISTIU usando status_final_map.
    """
    if df_scope.empty:
        return df_scope.copy()

    if status_venda is None:
        status_venda = ["VENDA GERADA", "VENDA INFORMADA"]

    s = df_scope["STATUS_BASE"].fillna("").astype(str).str.upper()
    df2 = df_scope[s.isin([x.upper() for x in status_venda])].copy()
    if df2.empty:
        return df2

    # Garante colunas do cliente
    df2["NOME_CLIENTE_BASE"] = (
        df2.get("NOME_CLIENTE_BASE", df2.get("CLIENTE", "NÃO INFORMADO"))
        .fillna("NÃO INFORMADO")
        .astype(str)
        .str.upper()
        .str.strip()
    )
    df2["CPF_CLIENTE_BASE"] = (
        df2.get("CPF_CLIENTE_BASE", df2.get("CPF", ""))
        .fillna("")
        .astype(str)
        .str.replace(r"\D", "", regex=True)
    )

    df2["CHAVE_CLIENTE"] = (
        df2["NOME_CLIENTE_BASE"].astype(str).str.upper().str.strip()
        + " | "
        + df2["CPF_CLIENTE_BASE"].astype(str).str.strip()
    )

    # 🔥 aplica regra DESISTIU
    if status_final_map is not None:
        df2 = df2.merge(status_final_map, on="CHAVE_CLIENTE", how="left")
        df2 = df2[df2["STATUS_FINAL_CLIENTE"] != "DESISTIU"]

    if df2.empty:
        return df2

    df2 = df2.sort_values("DIA")
    return df2.groupby("CHAVE_CLIENTE").tail(1).copy()


# ---------------------------------------------------------
# CONFIG PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Funil do Corretor",
    page_icon="🧑‍💼",
    layout="wide",
)

st.title("🧑‍💼 Funil Individual do Corretor")
st.caption("Regra do DESISTIU totalmente aplicada – venda só vale se o último status não for DESISTIU.")


# ---------------------------------------------------------
# CARREGA BASE
# ---------------------------------------------------------
df = carregar_dados_planilha()

if df.empty:
    st.error("Erro ao carregar planilha.")
    st.stop()

df["DIA"] = pd.to_datetime(df["DIA"], errors="coerce")

# NORMALIZA STATUS
df["STATUS_BASE"] = (
    df.get("STATUS_BASE", "")
    .fillna("")
    .astype(str)
    .str.upper()
)
df.loc[df["STATUS_BASE"].str.contains("DESIST", na=False), "STATUS_BASE"] = "DESISTIU"

# DEFINE NOME / CPF / CHAVE_CLIENTE
poss_nome = ["NOME_CLIENTE_BASE", "CLIENTE", "NOME", "NOME CLIENTE"]
poss_cpf = ["CPF_CLIENTE_BASE", "CPF", "CPF CLIENTE"]

col_nome = next((c for c in poss_nome if c in df.columns), None)
col_cpf = next((c for c in poss_cpf if c in df.columns), None)

df["NOME_CLIENTE_BASE"] = (
    df[col_nome].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
    if col_nome else "NÃO INFORMADO"
)

df["CPF_CLIENTE_BASE"] = (
    df[col_cpf].fillna("").astype(str).str.replace(r"\D", "", regex=True)
    if col_cpf else ""
)

df["CHAVE_CLIENTE"] = (
    df["NOME_CLIENTE_BASE"].astype(str).str.upper().str.strip()
    + " | "
    + df["CPF_CLIENTE_BASE"].astype(str).str.strip()
)

# ---------------------------------------------------------
# 🔥 STATUS FINAL GLOBAL (regra principal do DESISTIU)
# ---------------------------------------------------------
df_sorted = df.sort_values("DIA")
status_final_por_cliente = (
    df_sorted.groupby("CHAVE_CLIENTE")["STATUS_BASE"]
    .last()
    .fillna("")
    .astype(str)
    .str.upper()
)
status_final_por_cliente.name = "STATUS_FINAL_CLIENTE"


# ---------------------------------------------------------
# FILTROS – CORRETOR
# ---------------------------------------------------------
corretores = sorted(df["CORRETOR"].dropna().astype(str).unique())
st.sidebar.title("Filtros do corretor")

corretor_sel = st.sidebar.selectbox("Selecione o corretor", corretores)

df_cor = df[df["CORRETOR"] == corretor_sel].copy()
if df_cor.empty:
    st.warning("Nenhum dado para esse corretor.")
    st.stop()


# ---------------------------------------------------------
# DATA BASE
# ---------------------------------------------------------
if "DATA BASE" in df_cor.columns:
    df_cor["DATA_BASE"] = df_cor["DATA BASE"].astype(str).apply(mes_ano_ptbr_para_date)
    df_cor["DATA_BASE_LABEL"] = df_cor["DATA_BASE"].apply(
        lambda d: d.strftime("%m/%Y") if pd.notnull(d) else ""
    )
else:
    df_cor["DATA_BASE"] = df_cor["DIA"]
    df_cor["DATA_BASE_LABEL"] = df_cor["DIA"].dt.strftime("%m/%Y")

bases_validas = (
    df_cor[["DATA_BASE", "DATA_BASE_LABEL"]]
    .dropna(subset=["DATA_BASE"])
    .drop_duplicates()
    .sort_values("DATA_BASE")
)

opcoes_bases = bases_validas["DATA_BASE_LABEL"].tolist()
default_bases = opcoes_bases[-2:] if len(opcoes_bases) >= 2 else opcoes_bases

bases_sel = st.sidebar.multiselect(
    "DATA BASE (mês comercial)",
    options=opcoes_bases,
    default=default_bases,
)

if not bases_sel:
    bases_sel = opcoes_bases

df_periodo = df_cor[df_cor["DATA_BASE_LABEL"].isin(bases_sel)].copy()
if df_periodo.empty:
    st.warning("Nenhum registro do corretor nas DATA BASE selecionadas.")
    st.stop()


# ---------------------------------------------------------
# VENDA: GERADA / INFORMADA / AMBAS
# ---------------------------------------------------------
radio_venda = st.sidebar.radio(
    "Tipo de venda",
    ("VENDA GERADA + INFORMADA", "Só VENDA GERADA"),
)

if radio_venda == "Só VENDA GERADA":
    status_venda = ["VENDA GERADA"]
    desc_venda = "apenas VENDA GERADA"
else:
    status_venda = ["VENDA GERADA", "VENDA INFORMADA"]
    desc_venda = "GERADA + INFORMADA"


# ---------------------------------------------------------
# INTERVALO REAL
# ---------------------------------------------------------
dias_validos = df_periodo["DIA"].dropna()
if not dias_validos.empty:
    data_ini = dias_validos.min().date()
    data_fim = dias_validos.max().date()
else:
    hoje = date.today()
    data_ini = hoje
    data_fim = hoje

st.caption(
    f"Corretor **{corretor_sel}** • DATA BASE: **{bases_sel}** • "
    f"Período: **{data_ini.strftime('%d/%m/%Y')} → {data_fim.strftime('%d/%m/%Y')}** • "
    f"Vendas consideradas: **{desc_venda}** (com DESISTIU aplicado)."
)


# ---------------------------------------------------------
# KPIs CORRETOR
# ---------------------------------------------------------
st.markdown("## 📌 Funil do período (corretor)")

status_col = df_periodo["STATUS_BASE"].fillna("").astype(str).str.upper()

analises_em = conta_analises_base(status_col)
reanalises = conta_reanalises(status_col)
aprovacoes = conta_aprovacoes(status_col)

# 🔥 VENDAS COM DESISTIU
df_vendas = obter_vendas_unicas(
    df_periodo,
    status_venda=status_venda,
    status_final_map=status_final_por_cliente,
)
vendas = len(df_vendas)
vgv = df_vendas.get("VGV", pd.Series([])).sum() if not df_vendas.empty else 0.0

# KPIs
c1, c2, c3 = st.columns(3)
c1.metric("Análises (EM)", analises_em)
c2.metric("Aprovações", aprovacoes)
c3.metric("Vendas (únicas) – DESISTIU aplicado", vendas)

c4, c5 = st.columns(2)
c4.metric("Reanálises", reanalises)
c5.metric("VGV total", format_currency(vgv))

st.markdown("---")


# ---------------------------------------------------------
# PLANEJAMENTO – METAS
# ---------------------------------------------------------
st.markdown("## 🎯 Planejamento baseado no funil do corretor")

if vendas > 0:
    anal_por_venda = analises_em / vendas if vendas > 0 else 0
    aprov_por_venda = aprovacoes / vendas if vendas > 0 else 0

    meta_v = st.number_input(
        "Meta de vendas para o próximo período",
        min_value=0,
        value=vendas,
        step=1,
    )

    if meta_v > 0:
        anal_necess = int(np.ceil(anal_por_venda * meta_v))
        aprov_necess = int(np.ceil(aprov_por_venda * meta_v))

        m1, m2, m3 = st.columns(3)
        m1.metric("Meta de vendas", meta_v)
        m2.metric("Análises necessárias", anal_necess)
        m3.metric("Aprovações necessárias", aprov_necess)

        st.markdown("### 📊 Acompanhamento da Meta – corretor")

        periodo_meta = st.date_input(
            "Período do acompanhamento",
            value=(data_ini, data_fim),
        )

        if isinstance(periodo_meta, tuple):
            ini, fim = periodo_meta
        else:
            ini, fim = data_ini, data_fim

        dr = pd.date_range(ini, fim, freq="D")
        dias_meta = [d.date() for d in dr]

        if dias_meta:
            df_periodo["DIA_DATA"] = df_periodo["DIA"].dt.date

            indicador = st.selectbox(
                "Indicador",
                ["Análises", "Aprovações", "Vendas"],
            )

            if indicador == "Análises":
                df_temp = df_periodo[
                    df_periodo["STATUS_BASE"] == "EM ANÁLISE"
                ]
                total_meta = anal_necess

            elif indicador == "Aprovações":
                df_temp = df_periodo[
                    df_periodo["STATUS_BASE"] == "APROVADO"
                ]
                total_meta = aprov_necess

            else:  # Vendas
                df_temp = obter_vendas_unicas(
                    df_periodo,
                    status_venda=status_venda,
                    status_final_map=status_final_por_cliente,
                )
                total_meta = meta_v

            if df_temp.empty or total_meta == 0:
                st.info("Não há dados suficientes para exibir o gráfico.")
            else:
                df_temp["DIA_DATA"] = pd.to_datetime(df_temp["DIA"]).dt.date
                cont_por_dia = (
                    df_temp.groupby("DIA_DATA")
                    .size()
                    .reindex(dias_meta, fill_value=0)
                )

                # prepara acumulado
                df_line = pd.DataFrame(
                    {"DIA": pd.to_datetime(dias_meta), "Real": cont_por_dia.values}
                )
                df_line["Real"] = df_line["Real"].cumsum()

                ultimo_mov = df_temp["DIA_DATA"].max()
                if pd.notnull(ultimo_mov):
                    df_line.loc[
                        df_line["DIA"].dt.date > ultimo_mov, "Real"
                    ] = np.nan

                df_line["Meta"] = np.linspace(0, total_meta, len(df_line))
                df_plot = df_line.melt("DIA", var_name="Série", value_name="Valor")

                chart = (
                    alt.Chart(df_plot)
                    .mark_line(point=True)
                    .encode(
                        x="DIA:T",
                        y="Valor:Q",
                        color="Série:N",
                    )
                    .properties(height=300)
                )

                st.altair_chart(chart, use_container_width=True)

