import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
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

# Cabeçalho com logo + título
col_logo, col_title = st.columns([1, 4])
with col_logo:
    try:
        st.image("logo_mr.png", width=160)
    except Exception:
        st.write("")
with col_title:
    st.title("🔻 Funil de Vendas – Visão Imobiliária")
    st.caption(
        "Visão consolidada da MR Imóveis: produtividade da equipe, funil de análises → "
        "aprovações → vendas e previsibilidade com base nos últimos 3 meses."
    )


# ---------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------
def conta_analises_total(status: pd.Series) -> int:
    s = status.fillna("").astype(str).str.upper()
    return s.isin(["EM ANÁLISE", "REANÁLISE"]).sum()


def conta_analises_base(status: pd.Series) -> int:
    s = status.fillna("").astype(str).str.upper()
    return (s == "EM ANÁLISE").sum()


def conta_reanalises(status: pd.Series) -> int:
    s = status.fillna("").astype(str).str.upper()
    return (s == "REANÁLISE").sum()


def conta_aprovacoes(status: pd.Series) -> int:
    s = status.fillna("").astype(str).str.upper()
    return (s == "APROVADO").sum()


def obter_vendas_unicas(
    df_scope: pd.DataFrame,
    status_venda=None,
) -> pd.DataFrame:
    """
    Retorna uma venda por cliente (último status).
    Se tiver VENDA INFORMADA e depois VENDA GERADA, fica só a GERADA.
    """
    if df_scope.empty:
        return df_scope.copy()

    if status_venda is None:
        status_venda = ["VENDA GERADA", "VENDA INFORMADA"]

    s = df_scope["STATUS_BASE"].fillna("").astype(str).str.upper()
    df_v = df_scope[s.isin(status_venda)].copy()
    if df_v.empty:
        return df_v

    # Garante colunas de cliente
    if "NOME_CLIENTE_BASE" not in df_v.columns:
        if "CLIENTE" in df_v.columns:
            df_v["NOME_CLIENTE_BASE"] = (
                df_v["CLIENTE"]
                .fillna("NÃO INFORMADO")
                .astype(str)
                .str.upper()
                .str.strip()
            )
        else:
            df_v["NOME_CLIENTE_BASE"] = "NÃO INFORMADO"

    if "CPF_CLIENTE_BASE" not in df_v.columns:
        df_v["CPF_CLIENTE_BASE"] = ""

    df_v["CHAVE_CLIENTE"] = (
        df_v["NOME_CLIENTE_BASE"]
        .fillna("NÃO INFORMADO")
        .astype(str)
        .str.upper()
        .str.strip()
        + " | "
        + df_v["CPF_CLIENTE_BASE"].fillna("").astype(str).str.strip()
    )

    # Ordena por DIA para pegar o último status do cliente
    if "DIA" in df_v.columns:
        df_v = df_v.sort_values("DIA")
    df_ult = df_v.groupby("CHAVE_CLIENTE").tail(1).copy()
    return df_ult


def format_currency(valor: float) -> str:
    try:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


# ---------------------------------------------------------
# CARREGA A BASE DA PLANILHA
# ---------------------------------------------------------
df = carregar_dados_planilha()

if df.empty:
    st.error("Não foi possível carregar os dados da planilha.")
    st.stop()

# DIA e DATA_BASE em datetime, DATA_BASE_LABEL já vem do app_dashboard
df["DIA"] = pd.to_datetime(df.get("DIA"), errors="coerce")

if "DATA_BASE" in df.columns:
    df["DATA_BASE"] = pd.to_datetime(df["DATA_BASE"], errors="coerce")
else:
    df["DATA_BASE"] = df["DIA"]

if "DATA_BASE_LABEL" not in df.columns:
    df["DATA_BASE_LABEL"] = df["DATA_BASE"].dt.strftime("%m/%Y")

dias_validos = df["DIA"].dropna()
bases_validas = df["DATA_BASE"].dropna()

# Limites de datas de movimentação
hoje = date.today()
if dias_validos.empty:
    data_min_mov = hoje - timedelta(days=30)
    data_max_mov = hoje
else:
    data_min_mov = dias_validos.min().date()
    data_max_mov = dias_validos.max().date()

# Permitimos selecionar datas futuras até 1 ano à frente
max_futuro = max(data_max_mov, hoje) + timedelta(days=365)


# ---------------------------------------------------------
# SIDEBAR – DOIS SELETORES (DIA + DATA BASE)
# ---------------------------------------------------------
st.sidebar.title("Filtros da visão imobiliária")

# 1) Período por DIA (data de movimentação)
data_ini_default_mov = max(data_min_mov, (data_max_mov - timedelta(days=30)))
periodo_mov = st.sidebar.date_input(
    "Período (data de movimentação)",
    value=(data_ini_default_mov, data_max_mov),
    min_value=data_min_mov,
    max_value=max_futuro,
)

if isinstance(periodo_mov, tuple):
    data_ini_mov, data_fim_mov = periodo_mov
else:
    data_ini_mov = periodo_mov
    data_fim_mov = periodo_mov

if data_ini_mov > data_fim_mov:
    data_ini_mov, data_fim_mov = data_fim_mov, data_ini_mov

mask_dia = (df["DIA"].dt.date >= data_ini_mov) & (df["DIA"].dt.date <= data_fim_mov)
df_periodo = df[mask_dia].copy()

# 2) Período por DATA BASE (mês comercial) – mesma lógica do app principal
bases_df = (
    df[["DATA_BASE", "DATA_BASE_LABEL"]]
    .dropna(subset=["DATA_BASE"])
    .drop_duplicates(subset=["DATA_BASE_LABEL"])
    .sort_values("DATA_BASE")
)

opcoes_bases = bases_df["DATA_BASE_LABEL"].tolist()

if not opcoes_bases:
    st.error("Sem datas base válidas na planilha para filtrar.")
    st.stop()

default_bases = opcoes_bases[-2:] if len(opcoes_bases) >= 2 else opcoes_bases

bases_selecionadas = st.sidebar.multiselect(
    "Período por DATA BASE (mês comercial)",
    options=opcoes_bases,
    default=default_bases,
)

if not bases_selecionadas:
    # Se nada for marcado, considera todas as bases
    bases_selecionadas = opcoes_bases

df_periodo = df_periodo[df_periodo["DATA_BASE_LABEL"].isin(bases_selecionadas)].copy()

# Filtro de tipo de venda
opcao_venda = st.sidebar.radio(
    "Tipo de venda para o funil",
    ("VENDA GERADA + INFORMADA", "Só VENDA GERADA"),
    index=0,
)

if opcao_venda == "Só VENDA GERADA":
    status_venda_considerado = ["VENDA GERADA"]
    desc_venda = "apenas VENDA GERADA"
else:
    status_venda_considerado = ["VENDA GERADA", "VENDA INFORMADA"]
    desc_venda = "VENDA GERADA + VENDA INFORMADA"

# Caption do período (DIA + DATA BASE)
if len(bases_selecionadas) == 1:
    base_str = bases_selecionadas[0]
else:
    base_str = f"{bases_selecionadas[0]} até {bases_selecionadas[-1]}"

st.caption(
    f"Período (movimentação): **{data_ini_mov.strftime('%d/%m/%Y')}** até "
    f"**{data_fim_mov.strftime('%d/%m/%Y')}** • "
    f"DATA BASE: **{base_str}** • "
    f"Vendas consideradas no funil: **{desc_venda}**."
)

if df_periodo.empty:
    st.warning("Nenhum registro encontrado para o período selecionado.")
    st.stop()


# ---------------------------------------------------------
# KPIs PRINCIPAIS – FUNIL DO PERÍODO
# ---------------------------------------------------------
st.markdown("## 🧭 Funil da Imobiliária – Período Selecionado")

status_periodo = df_periodo["STATUS_BASE"].fillna("").astype(str).str.upper()

analises_em = conta_analises_base(status_periodo)
reanalises = conta_reanalises(status_periodo)
analises_total = conta_analises_total(status_periodo)
aprovacoes = conta_aprovacoes(status_periodo)

df_vendas_periodo = obter_vendas_unicas(
    df_periodo,
    status_venda=status_venda_considerado,
)
vendas = len(df_vendas_periodo)
vgv_total = df_vendas_periodo["VGV"].sum() if not df_vendas_periodo.empty else 0.0

taxa_aprov_analise = (aprovacoes / analises_em * 100) if analises_em > 0 else 0.0
taxa_venda_analise = (vendas / analises_em * 100) if analises_em > 0 else 0.0
taxa_venda_aprov = (vendas / aprovacoes * 100) if aprovacoes > 0 else 0.0

corretores_ativos_periodo = df_periodo["CORRETOR"].dropna().astype(str).nunique()
ipc_periodo = (vendas / corretores_ativos_periodo) if corretores_ativos_periodo > 0 else None

# ---------------------------------------------------------
# LEADS DO PERÍODO (CRM SUPREMO VIA SESSION_STATE)
# ---------------------------------------------------------
df_leads = st.session_state.get("df_leads", pd.DataFrame())

total_leads_periodo = None
conv_leads_analise_pct = None
leads_por_analise = None

if not df_leads.empty and "data_captura" in df_leads.columns:
    df_leads_use = df_leads.dropna(subset=["data_captura"]).copy()
    df_leads_use["data_captura"] = pd.to_datetime(
        df_leads_use["data_captura"], errors="coerce"
    )
    df_leads_use["data_captura_date"] = df_leads_use["data_captura"].dt.date

    mask_leads_periodo = (
        (df_leads_use["data_captura_date"] >= data_ini_mov)
        & (df_leads_use["data_captura_date"] <= data_fim_mov)
    )
    df_leads_periodo = df_leads_use[mask_leads_periodo].copy()

    total_leads_periodo = len(df_leads_periodo)

    if total_leads_periodo > 0:
        conv_leads_analise_pct = (
            analises_em / total_leads_periodo * 100 if analises_em > 0 else 0.0
        )
        leads_por_analise = (
            total_leads_periodo / analises_em if analises_em > 0 else None
        )

# ---------------------------------------------------------
# BLOCO PRINCIPAL DO FUNIL
# ---------------------------------------------------------
lc1, lc2, lc3 = st.columns(3)
with lc1:
    st.metric(
        "Leads (CRM – período)",
        total_leads_periodo if total_leads_periodo is not None else "—",
    )
with lc2:
    if conv_leads_analise_pct is not None:
        st.metric(
            "Leads → Análises (só EM)",
            f"{conv_leads_analise_pct:.1f}%",
        )
    else:
        st.metric("Leads → Análises (só EM)", "—")
with lc3:
    if leads_por_analise is not None:
        st.metric(
            "Relação leads/análise (só EM)",
            f"{leads_por_analise:.1f} leads/análise",
        )
    else:
        st.metric("Relação leads/análise (só EM)", "—")

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
    st.metric("Taxa Aprov./Análises (só EM)", f"{taxa_aprov_analise:.1f}%")
with c8:
    st.metric("Taxa Vendas/Análises (só EM)", f"{taxa_venda_analise:.1f}%")

c9, c10 = st.columns(2)
with c9:
    st.metric("Taxa Vendas/Aprovações", f"{taxa_venda_aprov:.1f}%")
with c10:
    st.metric(
        "IPC do período (vendas/corretor)",
        f"{ipc_periodo:.2f}" if ipc_periodo is not None else "—",
    )

# Gráfico do funil no período
st.markdown("### 📊 Gráfico do funil (período selecionado)")
dados_funil = pd.DataFrame(
    {
        "Etapa": ["Análises (EM)", "Reanálises", "Aprovações", "Vendas"],
        "Quantidade": [analises_em, reanalises, aprovacoes, vendas],
    }
)

chart_funil = (
    alt.Chart(dados_funil)
    .mark_bar()
    .encode(
        x=alt.X("Etapa:N", sort=None, title="Etapas do funil"),
        y=alt.Y("Quantidade:Q", title="Quantidade"),
        tooltip=["Etapa", "Quantidade"],
    )
)
st.altair_chart(chart_funil, use_container_width=True)

st.markdown("---")


# ---------------------------------------------------------
# PRODUTIVIDADE – EQUIPE ATIVA
# ---------------------------------------------------------
st.markdown("## 👥 Produtividade da equipe – período selecionado")

if corretores_ativos_periodo == 0:
    st.info("Não há corretores com movimentação no período selecionado.")
else:
    if df_vendas_periodo.empty:
        corretores_com_venda_periodo = 0
    else:
        corretores_com_venda_periodo = (
            df_vendas_periodo["CORRETOR"].dropna().astype(str).nunique()
        )

    equipe_produtiva_pct = (
        corretores_com_venda_periodo / corretores_ativos_periodo * 100
        if corretores_ativos_periodo > 0
        else 0.0
    )

    vendas_periodo = vendas
    ipc_periodo_prod = ipc_periodo

    c11, c12, c13, c14 = st.columns(4)
    with c11:
        st.metric("Corretores ativos (período)", corretores_ativos_periodo)
    with c12:
        st.metric(
            "% equipe produtiva (período)",
            f"{equipe_produtiva_pct:.1f}%",
        )
    with c13:
        st.metric("Vendas (período – únicas)", vendas_periodo)
    with c14:
        st.metric(
            "IPC período (vendas/corretor)",
            f"{ipc_periodo_prod:.2f}" if ipc_periodo_prod is not None else "—",
        )

    st.caption(
        f"Período considerado (data de movimentação): "
        f"{data_ini_mov.strftime('%d/%m/%Y')} até {data_fim_mov.strftime('%d/%m/%Y')}."
    )

st.markdown("---")


# ---------------------------------------------------------
# HISTÓRICO – FUNIL DOS ÚLTIMOS 3 MESES (DATA BASE)
# ---------------------------------------------------------
st.markdown("## 📈 Funil histórico – últimos 3 meses (DATA BASE)")

analises_necessarias = 0
aprovacoes_necessarias = 0
meta_vendas = 0

if bases_validas.empty:
    st.info("Não há DATA BASE válida para calcular o histórico de 3 meses.")
else:
    data_ref_base = bases_validas.max()
    inicio_3m = data_ref_base - pd.DateOffset(months=3)

    mask_3m = (df["DATA_BASE"] >= inicio_3m) & (df["DATA_BASE"] <= data_ref_base)
    df_3m = df[mask_3m].copy()

    if df_3m.empty:
        st.info(
            f"Não há registros na janela dos últimos 3 meses de DATA BASE "
            f"(de {inicio_3m.date().strftime('%d/%m/%Y')} "
            f"até {data_ref_base.date().strftime('%d/%m/%Y')})."
        )
    else:
        status_3m = df_3m["STATUS_BASE"].fillna("").astype(str).str.upper()

        analises_3m = conta_analises_base(status_3m)
        aprov_3m = conta_aprovacoes(status_3m)
        df_vendas_3m = obter_vendas_unicas(
            df_3m,
            status_venda=status_venda_considerado,
        )
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
            st.metric("Corretores ativos (3m)", corretores_ativos_3m)
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

        st.metric(
            "Média de aprovações por venda (3m)",
            f"{aprovacoes_por_venda:.1f}" if vendas_3m > 0 else "—",
        )

        st.caption(
            f"Janela de análise (DATA BASE): de {inicio_3m.date().strftime('%d/%m/%Y')} "
            f"até {data_ref_base.date().strftime('%d/%m/%Y')}."
        )

        st.markdown("### 🎯 Planejamento com base no funil dos últimos 3 meses")

        meta_vendas = st.number_input(
            "Meta de vendas (imobiliária) para o próximo período",
            min_value=0,
            step=1,
            value=int(vendas_3m / 3) if vendas_3m > 0 else 10,
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
                )
            with c25:
                st.metric(
                    "Aprovações necessárias (aprox.)",
                    f"{aprovacoes_necessarias} aprovações",
                )

        # Gráfico histórico de vendas por DATA BASE (últimos 3 meses)
        st.markdown("### 📊 Vendas por DATA BASE (últimos 3 meses)")

        df_vendas_3m_chart = df_vendas_3m.copy()
        if "DATA_BASE_LABEL" not in df_vendas_3m_chart.columns:
            df_vendas_3m_chart["DATA_BASE_LABEL"] = df_vendas_3m_chart["DATA_BASE"].dt.strftime("%m/%Y")

        if df_vendas_3m_chart.empty:
            st.info("Não há vendas nos últimos 3 meses para montar o gráfico.")
        else:
            vendas_por_base = (
                df_vendas_3m_chart.dropna(subset=["DATA_BASE_LABEL"])
                .groupby("DATA_BASE_LABEL")
                .size()
                .reset_index(name="Vendas")
            )

            chart_hist = (
                alt.Chart(vendas_por_base)
                .mark_bar()
                .encode(
                    x=alt.X("DATA_BASE_LABEL:N", title="Data base (mês/ano)"),
                    y=alt.Y("Vendas:Q", title="Vendas únicas"),
                    tooltip=["DATA_BASE_LABEL", "Vendas"],
                )
            )
            st.altair_chart(chart_hist, use_container_width=True)
