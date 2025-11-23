import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import date, timedelta  # <-- acrescentei timedelta

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Funil de Vendas – MR Imóveis",
    page_icon="🔻",
    layout="wide",
)

st.title("🔻 Funil de Vendas – MR Imóveis")

# ---------------------------------------------------------
# CARREGAMENTO DA PLANILHA (GOOGLE SHEETS)
# ---------------------------------------------------------
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID_ANALISES = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ANALISES}"

@st.cache_data(ttl=600)
def carregar_dados_funil() -> pd.DataFrame:
    """Carrega e trata a base de análises/vendas direto do Google Sheets."""
    df_local = pd.read_csv(CSV_URL)
    df_local.columns = [c.strip().upper() for c in df_local.columns]

    # DATA / DIA
    possiveis_datas = ["DATA", "DIA", "DATA DA ANÁLISE"]
    col_data = next((c for c in possiveis_datas if c in df_local.columns), None)
    if col_data:
        df_local["DIA"] = pd.to_datetime(df_local[col_data], errors="coerce", dayfirst=True)
    else:
        df_local["DIA"] = pd.NaT

    # STATUS BASE
    if "SITUAÇÃO" in df_local.columns:
        df_local["STATUS_BASE"] = (
            df_local["SITUAÇÃO"].astype(str).str.upper().str.strip()
        )
    else:
        df_local["STATUS_BASE"] = ""

    # Normalização de alguns textos de status
    df_local.loc[
        df_local["STATUS_BASE"].str.contains("EM ANÁLISE", na=False),
        "STATUS_BASE",
    ] = "EM ANÁLISE"
    df_local.loc[
        df_local["STATUS_BASE"].str.contains("REANÁLISE", na=False),
        "STATUS_BASE",
    ] = "REANÁLISE"

    # Normalização de corretor e equipe
    for col in ["CORRETOR", "EQUIPE"]:
        if col in df_local.columns:
            df_local[col] = df_local[col].astype(str).str.upper().str.strip()
        else:
            df_local[col] = "NÃO INFORMADO"

    # VGV
    if "OBSERVAÇÕES" in df_local.columns:
        df_local["VGV"] = pd.to_numeric(df_local["OBSERVAÇÕES"], errors="coerce").fillna(0)
    else:
        df_local["VGV"] = 0

    return df_local

# ---------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------
def conta_analises(s):
    """Análises totais (EM + RE) – volume."""
    return s.isin(["EM ANÁLISE", "REANÁLISE"]).sum()

def conta_analises_base(s):
    """Análises para base de conversão – SOMENTE EM ANÁLISE."""
    return (s == "EM ANÁLISE").sum()

def conta_reanalises(s):
    """Quantidade de REANÁLISE."""
    return (s == "REANÁLISE").sum()

def conta_aprovacoes(s):
    return (s == "APROVADO").sum()

def conta_vendas(s):
    return s.isin(["VENDA GERADA", "VENDA INFORMADA"]).sum()

# ---------------------------------------------------------
# FUNIL GERAL DA IMOBILIÁRIA
# ---------------------------------------------------------
st.markdown("### 🏙️ Visão geral – Funil por Imobiliária")

df = carregar_dados_funil()

if df.empty:
    st.error("Não foi possível carregar a base de dados. Verifique o Google Sheets.")
    st.stop()

# ---------------------------------------------------------
# SIDEBAR – FILTROS
# ---------------------------------------------------------
st.sidebar.title("Filtros 🔎")

dias_validos = pd.Series(df["DIA"].dropna())

if not dias_validos.empty:
    data_min = dias_validos.min()
    data_max = dias_validos.max()
else:
    hoje = date.today()
    data_min = hoje - timedelta(days=30)
    data_max = hoje

periodo = st.sidebar.date_input(
    "Período (data de movimentação)",
    value=(data_min.date(), data_max.date()),
    min_value=data_min.date(),
    max_value=data_max.date(),
)

if isinstance(periodo, tuple):
    data_ini, data_fim = periodo
else:
    data_ini = periodo
    data_fim = periodo

# Filtro por equipe para os blocos que suportam "Todas"
equipes_disponiveis = ["Todas"] + sorted(df["EQUIPE"].dropna().unique().tolist())
equipe_sel = st.sidebar.selectbox("Equipe (para funis por equipe)", equipes_disponiveis)

# ---------------------------------------------------------
# APLICA FILTRO DE PERÍODO
# ---------------------------------------------------------
mask_periodo = (df["DIA"] >= pd.to_datetime(data_ini)) & (
    df["DIA"] <= pd.to_datetime(data_fim)
)
df_periodo = df[mask_periodo].copy()

if df_periodo.empty:
    st.warning("Nenhum registro encontrado para o período selecionado.")
    st.stop()

# ---------------------------------------------------------
# FUNIL GERAL – IMOBILIÁRIA (PERÍODO)
# ---------------------------------------------------------
st.markdown("## 🧭 Funil geral da imobiliária (período selecionado)")

analises_em = conta_analises_base(df_periodo["STATUS_BASE"])
reanalises = conta_reanalises(df_periodo["STATUS_BASE"])
analises_total = conta_analises(df_periodo["STATUS_BASE"])
aprovacoes = conta_aprovacoes(df_periodo["STATUS_BASE"])
vendas = conta_vendas(df_periodo["STATUS_BASE"])
vgv_total = df_periodo["VGV"].sum()

taxa_aprov = (aprovacoes / analises_em * 100) if analises_em > 0 else 0
taxa_venda_analises = (vendas / analises_em * 100) if analises_em > 0 else 0
taxa_venda_aprov = (vendas / aprovacoes * 100) if aprovacoes > 0 else 0

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.metric("Análises (só EM)", analises_em)
with c2:
    st.metric("Reanálises", reanalises)
with c3:
    st.metric("Análises (EM + RE)", analises_total)
with c4:
    st.metric("Aprovações", aprovacoes)
with c5:
    st.metric("Vendas (Total)", vendas)

c6, c7, c8 = st.columns(3)
with c6:
    st.metric(
        "VGV total",
        f"R$ {vgv_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
    )
with c7:
    st.metric("Taxa Aprov./Análises (só EM)", f"{taxa_aprov:.1f}%")
with c8:
    st.metric("Taxa Vendas/Análises (só EM)", f"{taxa_venda_analises:.1f}%")

c9, = st.columns(1)
with c9:
    st.metric("Taxa Vendas/Aprovações", f"{taxa_venda_aprov:.1f}%")

st.markdown("---")

# ---------------------------------------------------------
# FUNIL POR EQUIPE – TABELA COMPARATIVA
# ---------------------------------------------------------
st.markdown("## 👥 Funil por Equipe (comparativo)")

df_equipes = (
    df_periodo.groupby("EQUIPE")
    .agg(
        VGV=("VGV", "sum"),
        VENDAS=("STATUS_BASE", lambda s: conta_vendas(s)),
        ANALISES=("STATUS_BASE", lambda s: conta_analises(s)),
        ANALISES_BASE=("STATUS_BASE", lambda s: conta_analises_base(s)),
        REANALISES=("STATUS_BASE", lambda s: conta_reanalises(s)),
        APROVACOES=("STATUS_BASE", lambda s: conta_aprovacoes(s)),
    )
    .reset_index()
)

df_equipes["TAXA_APROV_ANALISES"] = (
    df_equipes.apply(
        lambda row: (row["APROVACOES"] / row["ANALISES_BASE"] * 100)
        if row["ANALISES_BASE"] > 0
        else 0,
        axis=1,
    )
)

df_equipes["TAXA_VENDAS_ANALISES"] = (
    df_equipes.apply(
        lambda row: (row["VENDAS"] / row["ANALISES_BASE"] * 100)
        if row["ANALISES_BASE"] > 0
        else 0,
        axis=1,
    )
)

df_equipes["TAXA_VENDAS_APROV"] = (
    df_equipes.apply(
        lambda row: (row["VENDAS"] / row["APROVACOES"] * 100)
        if row["APROVACOES"] > 0
        else 0,
        axis=1,
    )
)

df_equipes["VGV"] = df_equipes["VGV"].fillna(0)

df_equipes["VGV_FORMATADO"] = df_equipes["VGV"].apply(
    lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
)

df_equipes_vis = df_equipes[
    [
        "EQUIPE",
        "VGV_FORMATADO",
        "VENDAS",
        "ANALISES",
        "ANALISES_BASE",
        "REANALISES",
        "APROVACOES",
        "TAXA_APROV_ANALISES",
        "TAXA_VENDAS_ANALISES",
        "TAXA_VENDAS_APROV",
    ]
].copy()

df_equipes_vis.rename(
    columns={
        "EQUIPE": "Equipe",
        "VGV_FORMATADO": "VGV",
        "VENDAS": "Vendas",
        "ANALISES": "Análises (EM + RE)",
        "ANALISES_BASE": "Análises (só EM)",
        "REANALISES": "Reanálises",
        "APROVACOES": "Aprovações",
        "TAXA_APROV_ANALISES": "% Aprov./Análises (só EM)",
        "TAXA_VENDAS_ANALISES": "% Vendas/Análises (só EM)",
        "TAXA_VENDAS_APROV": "% Vendas/Aprovações",
    },
    inplace=True,
)

st.dataframe(
    df_equipes_vis.sort_values("VGV", ascending=False),
    use_container_width=True,
    hide_index=True,
)

st.markdown("---")

# ---------------------------------------------------------
# 🔍 Funil detalhado e planejamento por equipe
# ---------------------------------------------------------
st.markdown("## 🔍 Funil detalhado e planejamento por equipe")

if equipe_sel == "Todas":
    st.info("Selecione uma equipe específica na barra lateral para ver o funil e o planejamento dessa equipe.")
else:
    df_eq = df_periodo[df_periodo["EQUIPE"] == equipe_sel]

    if df_eq.empty:
        st.warning(f"A equipe **{equipe_sel}** não possui registros no período selecionado.")
    else:
        analises_eq_em = conta_analises_base(df_eq["STATUS_BASE"])   # só EM
        reanalises_eq = conta_reanalises(df_eq["STATUS_BASE"])       # só RE
        analises_eq_total = conta_analises(df_eq["STATUS_BASE"])     # EM + RE
        aprov_eq = conta_aprovacoes(df_eq["STATUS_BASE"])
        vendas_eq = conta_vendas(df_eq["STATUS_BASE"])
        vgv_eq = df_eq["VGV"].sum()

        taxa_aprov_eq = (
            aprov_eq / analises_eq_em * 100 if analises_eq_em > 0 else 0
        )
        taxa_venda_analises_eq = (
            vendas_eq / analises_eq_em * 100 if analises_eq_em > 0 else 0
        )

        taxa_venda_aprov_eq = (
            vendas_eq / aprov_eq * 100 if aprov_eq > 0 else 0
        )

        # ---------------------------------------------
        # IPC da equipe (Opção A) e Equipe Produtiva
        # ---------------------------------------------
        # Base completa da equipe (toda a linha do tempo)
        df_eq_full = df[df["EQUIPE"] == equipe_sel].copy()

        # Corretores da equipe ativos nos últimos 30 dias (qualquer movimentação)
        ipc_eq = None
        dias_eq_full = df_eq_full["DIA"].dropna()
        if not dias_eq_full.empty:
            data_max_eq_all = dias_eq_full.max()
            inicio_30_eq = data_max_eq_all - timedelta(days=30)
            df_eq_30 = df_eq_full[
                (df_eq_full["DIA"] >= inicio_30_eq) & (df_eq_full["DIA"] <= data_max_eq_all)
            ]
            corretores_ativos_30_eq = df_eq_30["CORRETOR"].dropna().nunique()
        else:
            corretores_ativos_30_eq = 0

        if corretores_ativos_30_eq > 0:
            ipc_eq = vendas_eq / corretores_ativos_30_eq

        # Equipe produtiva (% de corretores da equipe que venderam no período filtrado)
        corretores_totais_eq_periodo = df_eq["CORRETOR"].dropna().nunique()
        df_eq_vendas_periodo = df_eq[
            df_eq["STATUS_BASE"].isin(["VENDA GERADA", "VENDA INFORMADA"])
        ]
        corretores_com_venda_eq = df_eq_vendas_periodo["CORRETOR"].dropna().nunique()
        equipe_produtiva_eq = (
            (corretores_com_venda_eq / corretores_totais_eq_periodo) * 100
            if corretores_totais_eq_periodo > 0
            else 0
        )

        st.markdown(f"### Equipe: **{equipe_sel}**")

        # Cards da equipe
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric("Análises (só EM)", analises_eq_em)
        with c2:
            st.metric("Reanálises", reanalises_eq)
        with c3:
            st.metric("Análises (EM + RE)", analises_eq_total)
        with c4:
            st.metric("Aprovações", aprov_eq)
        with c5:
            st.metric("Vendas (Total)", vendas_eq)

        c6, c7, c8, c9, c10 = st.columns(5)
        with c6:
            st.metric(
                "VGV da equipe",
                f"R$ {vgv_eq:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            )
        with c7:
            st.metric(
                "IPC da equipe",
                f"{ipc_eq:.2f} vendas/corretor" if ipc_eq is not None else "—",
                help="Vendas da equipe no período selecionado ÷ corretores da equipe ativos nos últimos 30 dias.",
            )
        with c8:
            st.metric(
                "% Equipe produtiva",
                f"{equipe_produtiva_eq:.1f}%",
                help="Porcentagem de corretores da equipe que realizaram pelo menos 1 venda no período filtrado.",
            )
        with c9:
            st.metric("Taxa Aprov./Análises (só EM)", f"{taxa_aprov_eq:.1f}%")
        with c10:
            st.metric("Taxa Vendas/Análises (só EM)", f"{taxa_venda_analises_eq:.1f}%")

        c11, = st.columns(1)
        with c11:
            st.metric("Taxa Vendas/Aprovações", f"{taxa_venda_aprov_eq:.1f}%")

        # ---------------------------------------------
        # PLANEJAMENTO POR EQUIPE – ÚLTIMOS 3 MESES
        # ---------------------------------------------
        st.markdown("### 📊 Planejamento de vendas dessa equipe (base últimos 3 meses)")

        # Usa a base TOTAL mas filtrando pela equipe
        df_eq_full = df[df["EQUIPE"] == equipe_sel].copy()

        dt_eq_all = pd.to_datetime(df_eq_full["DIA"], errors="coerce")
        ref_date_eq = dt_eq_all.max()

        if pd.isna(ref_date_eq):
            st.info("Não foi possível identificar a data de referência da equipe na base.")
        else:
            limite_3m_eq = ref_date_eq - pd.DateOffset(months=3)
            mask_3m_eq = (dt_eq_all >= limite_3m_eq) & (dt_eq_all <= ref_date_eq)
            df_eq_3m = df_eq_full[mask_3m_eq].copy()

            if df_eq_3m.empty:
                st.info(
                    f"A equipe **{equipe_sel}** não possui registros nos últimos 3 meses "
                    f"(janela usada: {limite_3m_eq.date().strftime('%d/%m/%Y')} "
                    f"até {ref_date_eq.date().strftime('%d/%m/%Y')})."
                )
            else:
                analises_eq_3m_base = conta_analises_base(df_eq_3m["STATUS_BASE"])  # só EM ANÁLISE
                aprov_eq_3m = conta_aprovacoes(df_eq_3m["STATUS_BASE"])
                vendas_eq_3m = conta_vendas(df_eq_3m["STATUS_BASE"])

                if vendas_eq_3m > 0:
                    media_analise_por_venda_eq = (
                        analises_eq_3m_base / vendas_eq_3m
                        if analises_eq_3m_base > 0 else 0
                    )
                    media_aprov_por_venda_eq = (
                        aprov_eq_3m / vendas_eq_3m if aprov_eq_3m > 0 else 0
                    )
                else:
                    media_analise_por_venda_eq = 0
                    media_aprov_por_venda_eq = 0

                c10, c11, c12 = st.columns(3)
                with c10:
                    st.metric("Análises (3m – só EM)", analises_eq_3m_base)
                with c11:
                    st.metric("Aprovações (3m – equipe)", aprov_eq_3m)
                with c12:
                    st.metric("Vendas (3m – equipe)", vendas_eq_3m)

                st.caption(
                    f"Janela histórica usada para a equipe **{equipe_sel}**: "
                    f"de {limite_3m_eq.date().strftime('%d/%m/%Y')} "
                    f"até {ref_date_eq.date().strftime('%d/%m/%Y')}."
                )

                st.markdown("#### 🎯 Quantas análises/aprovações essa equipe precisa para bater a meta de vendas?")

                vendas_planejadas_eq = st.number_input(
                    "Vendas desejadas no mês para a equipe",
                    min_value=0,
                    step=1,
                    value=int(vendas_eq_3m / 3) if vendas_eq_3m > 0 else 0,
                    help="Sugestão inicial baseada na média mensal dos últimos 3 meses.",
                )

                if vendas_planejadas_eq > 0 and vendas_eq_3m > 0:
                    analises_eq_necessarias = vendas_planejadas_eq * media_analise_por_venda_eq
                    aprovacoes_eq_necessarias = vendas_planejadas_eq * media_aprov_por_venda_eq

                    analises_eq_necessarias_int = int(np.ceil(analises_eq_necessarias))
                    aprovacoes_eq_necessarias_int = int(np.ceil(aprovacoes_eq_necessarias))

                    c13, c14 = st.columns(2)
                    with c13:
                        st.metric(
                            "Análises necessárias (aprox.)",
                            f"{analises_eq_necessarias_int} análises",
                            help=(
                                f"Cálculo: {media_analise_por_venda_eq:.2f} análises/venda "
                                f"× {vendas_planejadas_eq}"
                            ),
                        )
                    with c14:
                        st.metric(
                            "Aprovações necessárias (aprox.)",
                            f"{aprovacoes_eq_necessarias_int} aprovações",
                            help=(
                                f"Cálculo: {media_aprov_por_venda_eq:.2f} aprovações/venda "
                                f"× {vendas_planejadas_eq}"
                            ),
                        )

                    st.caption(
                        "Os números são aproximados e arredondados para cima, "
                        "baseados no histórico real dessa equipe nos últimos 3 meses."
                    )
                elif vendas_planejadas_eq > 0 and vendas_eq_3m == 0:
                    st.info(
                        f"A equipe **{equipe_sel}** ainda não possui vendas registradas "
                        "nos últimos 3 meses, então não é possível estimar quantas análises/aprovações são necessárias."
                    )
                else:
                    st.info("Defina um número de vendas desejadas maior que zero para ver a projeção.")
