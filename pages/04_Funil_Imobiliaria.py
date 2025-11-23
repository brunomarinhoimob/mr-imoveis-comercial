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

col_logo, col_title = st.columns([1, 4])
with col_logo:
    try:
        st.image("logo_mr.png", width=160)
    except Exception:
        st.write("")  # se não achar a imagem, só ignora
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
df = carregar_dados_planilha()  :contentReference[oaicite:0]{index=0}

if df.empty:
    st.error("Não foi possível carregar os dados da planilha.")
    st.stop()

# Garante coluna DIA como datetime
df["DIA"] = pd.to_datetime(df["DIA"], errors="coerce")

# Garante coluna DATA_BASE como datetime (mês comercial)
col_data_base = None
for cand in ["DATA_BASE", "DATA BASE", "DATA_BASE_COMERCIAL", "DATA_BASE_MES"]:
    if cand in df.columns:
        col_data_base = cand
        break

if col_data_base is not None:
    df["DATA_BASE"] = pd.to_datetime(df[col_data_base], errors="coerce")
else:
    # fallback: se não tiver, usa a própria DIA como base
    df["DATA_BASE"] = df["DIA"]

dias_validos = df["DIA"].dropna()
bases_validas = df["DATA_BASE"].dropna()

if dias_validos.empty:
    hoje = date.today()
    data_min_mov = hoje - timedelta(days=30)
    data_max_mov = hoje
else:
    data_min_mov = dias_validos.min().date()
    data_max_mov = dias_validos.max().date()

if bases_validas.empty:
    data_min_base = data_min_mov
    data_max_base = data_max_mov
else:
    data_min_base = bases_validas.min().date()
    data_max_base = bases_validas.max().date()


# ---------------------------------------------------------
# SIDEBAR – PERÍODOS (MOVIMENTAÇÃO E DATA BASE)
# ---------------------------------------------------------
st.sidebar.title("Filtros da visão imobiliária")

# Período por data de movimentação (DIA)
data_ini_default_mov = max(data_min_mov, (data_max_mov - timedelta(days=30)))
periodo_mov = st.sidebar.date_input(
    "Período (data de movimentação)",
    value=(data_ini_default_mov, data_max_mov),
    min_value=data_min_mov,
    max_value=data_max_mov,
)

if isinstance(periodo_mov, tuple):
    data_ini_mov, data_fim_mov = periodo_mov
else:
    data_ini_mov = periodo_mov
    data_fim_mov = periodo_mov

if data_ini_mov > data_fim_mov:
    data_ini_mov, data_fim_mov = data_fim_mov, data_ini_mov

# Período por DATA_BASE (mês comercial)
base_ini_default = max(data_min_base, (data_max_base - timedelta(days=30)))
periodo_base = st.sidebar.date_input(
    "Período (DATA BASE – mês comercial)",
    value=(base_ini_default, data_max_base),
    min_value=data_min_base,
    max_value=data_max_base,
)

if isinstance(periodo_base, tuple):
    base_ini, base_fim = periodo_base
else:
    base_ini, base_fim = periodo_base, periodo_base

if base_ini > base_fim:
    base_ini, base_fim = base_fim, base_ini

mask_mov = (df["DIA"].dt.date >= data_ini_mov) & (df["DIA"].dt.date <= data_fim_mov)
mask_base_periodo = (df["DATA_BASE"].dt.date >= base_ini) & (
    df["DATA_BASE"].dt.date <= base_fim
)

mask_periodo = mask_mov & mask_base_periodo
df_periodo = df[mask_periodo].copy()

st.caption(
    f"Período (movimentação): **{data_ini_mov.strftime('%d/%m/%Y')}** até "
    f"**{data_fim_mov.strftime('%d/%m/%Y')}** · "
    f"DATA BASE de **{base_ini.strftime('%d/%m/%Y')}** até **{base_fim.strftime('%d/%m/%Y')}**."
)

if df_periodo.empty:
    st.warning("Nenhum registro encontrado para a combinação de filtros selecionada.")
    st.stop()


# ---------------------------------------------------------
# KPIs PRINCIPAIS – FUNIL DO PERÍODO (FILTRADO)
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
        help="Número médio de vendas únicas por corretor que atuou no período filtrado.",
    )

st.markdown("---")


# ---------------------------------------------------------
# PRODUTIVIDADE – EQUIPE ATIVA (ÚLTIMOS 30 DIAS POR DATA_BASE)
# ---------------------------------------------------------
st.markdown("## 👥 Produtividade da equipe – últimos 30 dias (DATA BASE)")

if bases_validas.empty:
    st.info("Não há datas válidas de DATA BASE na base para calcular os últimos 30 dias.")
else:
    data_ref_base = bases_validas.max()
    inicio_30 = data_ref_base - timedelta(days=30)

    mask_30 = (df["DATA_BASE"] >= inicio_30) & (df["DATA_BASE"] <= data_ref_base)
    df_30 = df[mask_30].copy()

    if df_30.empty:
        st.info(
            f"Não há movimentações nos últimos 30 dias de DATA BASE "
            f"(janela: {inicio_30.date().strftime('%d/%m/%Y')} "
            f"até {data_ref_base.date().strftime('%d/%m/%Y')})."
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
                "Corretores ativos (30 dias – DATA BASE)",
                corretores_ativos_30,
            )
        with c12:
            st.metric(
                "% equipe produtiva (30 dias)",
                f"{equipe_produtiva_pct:.1f}%",
                help="Corretor produtivo = pelo menos 1 venda única nesse período de DATA BASE.",
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
            f"Janela considerada pela DATA BASE: de {inicio_30.date().strftime('%d/%m/%Y')} "
            f"até {data_ref_base.date().strftime('%d/%m/%Y')}."
        )

st.markdown("---")


# ---------------------------------------------------------
# HISTÓRICO – FUNIL DOS ÚLTIMOS 3 MESES (DATA_BASE)
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

        # -------------------------------------------------
        # GRÁFICO DE LINHAS – ACOMPANHAMENTO DA META
        # -------------------------------------------------
        if meta_vendas > 0 and vendas_3m > 0 and not df_periodo.empty:
            st.markdown("### 📊 Acompanhamento da meta no período selecionado")

            indicador = st.selectbox(
                "Escolha o indicador para comparar com a meta",
                ["Análises", "Aprovações", "Vendas"],
            )

            # eixo de dias do período (movimentação)
            dias_periodo = (
                df_periodo["DIA"]
                .dt.date.dropna()
                .sort_values()
                .unique()
            )
            if len(dias_periodo) == 0:
                st.info("Não há datas válidas no período filtrado para montar o gráfico.")
            else:
                idx = pd.to_datetime(dias_periodo)
                df_line = pd.DataFrame(index=idx)
                df_line.index.name = "DIA"

                if indicador == "Análises":
                    df_temp = df_periodo[
                        df_periodo["STATUS_BASE"]
                        .fillna("")
                        .astype(str)
                        .str.upper()
                        == "EM ANÁLISE"
                    ].copy()
                    total_meta = analises_necessarias
                    label_real = "Análises acumuladas"
                elif indicador == "Aprovações":
                    df_temp = df_periodo[
                        df_periodo["STATUS_BASE"]
                        .fillna("")
                        .astype(str)
                        .str.upper()
                        == "APROVADO"
                    ].copy()
                    total_meta = aprovacoes_necessarias
                    label_real = "Aprovações acumuladas"
                else:  # Vendas
                    df_temp = obter_vendas_unicas(df_periodo).copy()
                    total_meta = meta_vendas
                    label_real = "Vendas acumuladas"

                if df_temp.empty or total_meta == 0:
                    st.info(
                        "Não há dados suficientes ou a meta está zerada para montar o gráfico."
                    )
                else:
                    df_temp["DIA_DATA"] = pd.to_datetime(df_temp["DIA"]).dt.date
                    cont_por_dia = (
                        df_temp.groupby("DIA_DATA")
                        .size()
                        .reindex(dias_periodo, fill_value=0)
                    )

                    df_line["Real"] = cont_por_dia.values
                    df_line["Real"] = df_line["Real"].cumsum()

                    df_line["Meta"] = np.linspace(
                        0, total_meta, num=len(df_line), endpoint=True
                    )

                    df_plot = (
                        df_line.reset_index()
                        .melt("DIA", var_name="Série", value_name="Valor")
                    )

                    chart = (
                        alt.Chart(df_plot)
                        .mark_line(point=True)
                        .encode(
                            x=alt.X("DIA:T", title="Dia (movimentação)"),
                            y=alt.Y("Valor:Q", title="Quantidade acumulada"),
                            color=alt.Color("Série:N", title=""),
                            tooltip=[
                                alt.Tooltip("DIA:T", title="Dia"),
                                alt.Tooltip("Série:N", title="Série"),
                                alt.Tooltip("Valor:Q", title="Quantidade"),
                            ],
                        )
                        .properties(height=320)
                    )

                    st.altair_chart(chart, use_container_width=True)
                    st.caption(
                        "Linha **Real** mostra o acumulado diário do indicador escolhido. "
                        "Linha **Meta** mostra o ritmo necessário para atingir a meta "
                        "no fim do período."
                    )

