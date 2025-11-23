import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta

from app_dashboard import carregar_dados_planilha

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Funil MR Imóveis – Imobiliária",
    page_icon="🔻",
    layout="wide",
)

st.title("🔻 Funil de Vendas – Visão Imobiliária")

st.caption(
    "Visão consolidada da MR Imóveis: produtividade da equipe, funil de análises → "
    "aprovações → vendas e previsibilidade com base nos últimos 3 meses."
)

# ---------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------
def conta_analises_total(status: pd.Series) -> int:
    """Análises totais (EM ANÁLISE + REANÁLISE)."""
    s = status.fillna("").astype(str).str.upper()
    return s.isin(["EM ANÁLISE", "REANÁLISE"]).sum()


def conta_analises_base(status: pd.Series) -> int:
    """Análises que entram na base de conversão: somente EM ANÁLISE."""
    s = status.fillna("").astype(str).str.upper()
    return (s == "EM ANÁLISE").sum()


def conta_reanalises(status: pd.Series) -> int:
    s = status.fillna("").astype(str).str.upper()
    return (s == "REANÁLISE").sum()


def conta_aprovacoes(status: pd.Series) -> int:
    s = status.fillna("").astype(str).str.upper()
    return (s == "APROVADO").sum()


def obter_vendas_unicas(df_scope: pd.DataFrame) -> pd.DataFrame:
    """Retorna uma venda por cliente (último status).
    Se tiver VENDA INFORMADA e depois VENDA GERADA, fica só a GERADA.
    """
    if df_scope.empty:
        return df_scope.copy()

    s = df_scope["STATUS_BASE"].fillna("").astype(str).str.upper()
    df_v = df_scope[s.isin(["VENDA GERADA", "VENDA INFORMADA"])].copy()
    if df_v.empty:
        return df_v

    # Garante colunas de cliente
    if "NOME_CLIENTE_BASE" not in df_v.columns:
        if "CLIENTE" in df_v.columns:
            df_v["NOME_CLIENTE_BASE"] = (
                df_v["CLIENTE"].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
            )
        else:
            df_v["NOME_CLIENTE_BASE"] = "NÃO INFORMADO"

    if "CPF_CLIENTE_BASE" not in df_v.columns:
        df_v["CPF_CLIENTE_BASE"] = ""

    df_v["CHAVE_CLIENTE"] = (
        df_v["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
        + " | "
        + df_v["CPF_CLIENTE_BASE"].fillna("").astype(str).str.strip()
    )

    df_v = df_v.sort_values("DIA")
    df_ult = df_v.groupby("CHAVE_CLIENTE").tail(1).copy()
    return df_ult


def format_currency(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------
# CARREGA A BASE DA PLANILHA (MESMA DO APP PRINCIPAL)
# ---------------------------------------------------------
df = carregar_dados_planilha()

if df.empty:
    st.error("Não foi possível carregar os dados da planilha.")
    st.stop()

# Garante coluna DIA como datetime
df["DIA"] = pd.to_datetime(df["DIA"], errors="coerce")

dias_validos = df["DIA"].dropna()
if dias_validos.empty:
    hoje = date.today()
    data_min = hoje - timedelta(days=30)
    data_max = hoje
else:
    data_min = dias_validos.min().date()
    data_max = dias_validos.max().date()

# ---------------------------------------------------------
# SIDEBAR – PERÍODO
# ---------------------------------------------------------
st.sidebar.title("Filtros da visão imobiliária")

# Sugestão de período padrão: últimos 30 dias
data_ini_default = max(data_min, (data_max - timedelta(days=30)))

periodo = st.sidebar.date_input(
    "Período (data de movimentação)",
    value=(data_ini_default, data_max),
    min_value=data_min,
    max_value=data_max,
)

if isinstance(periodo, tuple):
    data_ini, data_fim = periodo
else:
    data_ini = periodo
    data_fim = periodo

# Garante ordem correta
if data_ini > data_fim:
    data_ini, data_fim = data_fim, data_ini

mask_periodo = (df["DIA"].dt.date >= data_ini) & (df["DIA"].dt.date <= data_fim)
df_periodo = df[mask_periodo].copy()

st.caption(
    f"Período selecionado: **{data_ini.strftime('%d/%m/%Y')}** até "
    f"**{data_fim.strftime('%d/%m/%Y')}**."
)

if df_periodo.empty:
    st.warning("Nenhum registro encontrado para o período selecionado.")
    st.stop()

# ---------------------------------------------------------
# KPIs PRINCIPAIS – FUNIL DO PERÍODO
# ---------------------------------------------------------
status_periodo = df_periodo["STATUS_BASE"].fillna("").astype(str).str.upper()

analises_em = conta_analises_base(status_periodo)
reanalises = conta_reanalises(status_periodo)
analises_total = conta_analises_total(status_periodo)
aprovacoes = conta_aprovacoes(status_periodo)

df_vendas_periodo = obter_vendas_unicas(df_periodo)
vendas = len(df_vendas_periodo)
vgv_total = df_vendas_periodo["VGV"].sum() if not df_vendas_periodo.empty else 0.0

taxa_aprov_analise = (aprovacoes / analises_em * 100) if analises_em > 0 else 0.0
taxa_venda_analise = (vendas / analises_em * 100) if analises_em > 0 else 0.0
taxa_venda_aprov = (vendas / aprovacoes * 100) if aprovacoes > 0 else 0.0

corretores_ativos_periodo = df_periodo["CORRETOR"].dropna().astype(str).nunique()
ipc_periodo = (vendas / corretores_ativos_periodo) if corretores_ativos_periodo > 0 else None

st.markdown("## 🧭 Funil da Imobiliária – Período Selecionado")

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
    st.metric("Vendas (únicas)", vendas)

c6, c7, c8 = st.columns(3)
with c6:
    st.metric("VGV total", format_currency(vgv_total))
with c7:
    st.metric(
        "Taxa Aprov./Análises (só EM)",
        f"{taxa_aprov_analise:.1f}%",
    )
with c8:
    st.metric(
        "Taxa Vendas/Análises (só EM)",
        f"{taxa_venda_analise:.1f}%",
    )

c9, c10 = st.columns(2)
with c9:
    st.metric(
        "Taxa Vendas/Aprovações",
        f"{taxa_venda_aprov:.1f}%",
    )
with c10:
    st.metric(
        "IPC do período (vendas/corretor)",
        f"{ipc_periodo:.2f}" if ipc_periodo is not None else "—",
        help="Número médio de vendas únicas por corretor que atuou no período selecionado.",
    )

st.markdown("---")

# ---------------------------------------------------------
# PRODUTIVIDADE – EQUIPE ATIVA (ÚLTIMOS 30 DIAS)
# ---------------------------------------------------------
st.markdown("## 👥 Produtividade da equipe – últimos 30 dias")

if dias_validos.empty:
    st.info("Não há datas válidas na base para calcular os últimos 30 dias.")
else:
    data_ref = dias_validos.max()
    inicio_30 = data_ref - timedelta(days=30)

    mask_30 = (df["DIA"] >= inicio_30) & (df["DIA"] <= data_ref)
    df_30 = df[mask_30].copy()

    if df_30.empty:
        st.info(
            f"Não há movimentações nos últimos 30 dias "
            f"(janela: {inicio_30.date().strftime('%d/%m/%Y')} "
            f"até {data_ref.date().strftime('%d/%m/%Y')})."
        )
    else:
        df_vendas_30 = obter_vendas_unicas(df_30)

        corretores_ativos_30 = df_30["CORRETOR"].dropna().astype(str).nunique()
        corretores_com_venda_30 = (
            df_vendas_30["CORRETOR"].dropna().astype(str).nunique()
            if not df_vendas_30.empty
            else 0
        )

        equipe_produtiva_pct = (
            (corretores_com_venda_30 / corretores_ativos_30 * 100)
            if corretores_ativos_30 > 0
            else 0.0
        )

        vendas_30 = len(df_vendas_30)
        vgv_30 = df_vendas_30["VGV"].sum() if not df_vendas_30.empty else 0.0

        ipc_30 = (vendas_30 / corretores_ativos_30) if corretores_ativos_30 > 0 else None

        c11, c12, c13, c14 = st.columns(4)
        with c11:
            st.metric(
                "Corretores ativos (30 dias)",
                corretores_ativos_30,
            )
        with c12:
            st.metric(
                "% equipe produtiva (30 dias)",
                f"{equipe_produtiva_pct:.1f}%",
                help="Corretor produtivo = pelo menos 1 venda única nos últimos 30 dias.",
            )
        with c13:
            st.metric(
                "Vendas (30 dias – únicas)",
                vendas_30,
            )
        with c14:
            st.metric(
                "IPC 30 dias (vendas/corretor)",
                f"{ipc_30:.2f}" if ipc_30 is not None else "—",
            )

        st.caption(
            f"Janela considerada: de {inicio_30.date().strftime('%d/%m/%Y')} "
            f"até {data_ref.date().strftime('%d/%m/%Y')}."
        )

st.markdown("---")

# ---------------------------------------------------------
# HISTÓRICO – FUNIL DOS ÚLTIMOS 3 MESES
# ---------------------------------------------------------
st.markdown("## 📈 Funil histórico – últimos 3 meses")

if dias_validos.empty:
    st.info("Não há datas válidas para calcular o histórico de 3 meses.")
else:
    data_ref = dias_validos.max()
    inicio_3m = data_ref - pd.DateOffset(months=3)

    mask_3m = (df["DIA"] >= inicio_3m) & (df["DIA"] <= data_ref)
    df_3m = df[mask_3m].copy()

    if df_3m.empty:
        st.info(
            f"Não há registros na janela dos últimos 3 meses "
            f"(de {inicio_3m.date().strftime('%d/%m/%Y')} "
            f"até {data_ref.date().strftime('%d/%m/%Y')})."
        )
    else:
        status_3m = df_3m["STATUS_BASE"].fillna("").astype(str).str.upper()

        analises_3m = conta_analises_base(status_3m)  # só EM ANÁLISE como base
        aprov_3m = conta_aprovacoes(status_3m)
        df_vendas_3m = obter_vendas_unicas(df_3m)
        vendas_3m = len(df_vendas_3m)
        vgv_3m = df_vendas_3m["VGV"].sum() if not df_vendas_3m.empty else 0.0

        corretores_ativos_3m = df_3m["CORRETOR"].dropna().astype(str).nunique()
        ipc_3m = (vendas_3m / corretores_ativos_3m) if corretores_ativos_3m > 0 else None

        if vendas_3m > 0:
            analises_por_venda = analises_3m / vendas_3m if analises_3m > 0 else 0.0
            aprovacoes_por_venda = aprov_3m / vendas_3m if aprov_3m > 0 else 0.0
        else:
            analises_por_venda = 0.0
            aprovacoes_por_venda = 0.0

        c15, c16, c17, c18 = st.columns(4)
        with c15:
            st.metric("Análises (3m – só EM)", analises_3m)
        with c16:
            st.metric("Aprovações (3m)", aprov_3m)
        with c17:
            st.metric("Vendas (3m – únicas)", vendas_3m)
        with c18:
            st.metric("VGV (3m)", format_currency(vgv_3m))

        c19, c20, c21 = st.columns(3)
        with c19:
            st.metric(
                "Corretores ativos (3m)",
                corretores_ativos_3m,
            )
        with c20:
            st.metric(
                "IPC 3m (vendas/corretor)",
                f"{ipc_3m:.2f}" if ipc_3m is not None else "—",
            )
        with c21:
            st.metric(
                "Média de análises por venda (3m)",
                f"{analises_por_venda:.1f}" if vendas_3m > 0 else "—",
            )

        c22, = st.columns(1)
        with c22:
            st.metric(
                "Média de aprovações por venda (3m)",
                f"{aprovacoes_por_venda:.1f}" if vendas_3m > 0 else "—",
            )

        st.caption(
            f"Janela de análise: de {inicio_3m.date().strftime('%d/%m/%Y')} "
            f"até {data_ref.date().strftime('%d/%m/%Y')}."
        )

        st.markdown("### 🎯 Planejamento com base no funil dos últimos 3 meses")

        meta_vendas = st.number_input(
            "Meta de vendas (imobiliária) para o próximo período",
            min_value=0,
            step=1,
            value=int(vendas_3m / 3) if vendas_3m > 0 else 10,
            help="Use a meta de vendas do mês ou do período que você quer planejar.",
        )

        if meta_vendas > 0 and vendas_3m > 0:
            analises_necessarias = int(np.ceil(analises_por_venda * meta_vendas))
            aprovacoes_necessarias = int(np.ceil(aprovacoes_por_venda * meta_vendas))

            c23, c24, c25 = st.columns(3)
            with c23:
                st.metric("Meta de vendas (planejada)", meta_vendas)
            with c24:
                st.metric(
                    "Análises necessárias (aprox.)",
                    f"{analises_necessarias} análises",
                    help=(
                        f"Cálculo: {analises_por_venda:.2f} análises/venda × "
                        f"{meta_vendas} vendas planejadas."
                    ),
                )
            with c25:
                st.metric(
                    "Aprovações necessárias (aprox.)",
                    f"{aprovacoes_necessarias} aprovações",
                    help=(
                        f"Cálculo: {aprovacoes_por_venda:.2f} aprovações/venda × "
                        f"{meta_vendas} vendas planejadas."
                    ),
                )

            st.caption(
                "Esses números são aproximados e baseados no comportamento real da "
                "imobiliária nos últimos 3 meses (não é chute, é dado)."
            )
        elif meta_vendas > 0 and vendas_3m == 0:
            st.info(
                "Ainda não há vendas registradas nos últimos 3 meses para calcular "
                "a previsibilidade do funil."
            )
