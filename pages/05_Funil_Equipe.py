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
    page_title="Funil MR Imóveis – Equipe",
    page_icon="🧩",
    layout="wide",
)

# ---------------------------------------------------------
# CARREGA BASE GERAL
# ---------------------------------------------------------
df_global = carregar_dados_planilha()

if df_global.empty:
    st.error("Não foi possível carregar os dados da planilha.")
    st.stop()

# Garante DIA como datetime
df_global["DIA"] = pd.to_datetime(df_global["DIA"], errors="coerce")

# Lista de equipes
if "EQUIPE" not in df_global.columns:
    st.error("Coluna 'EQUIPE' não encontrada na base.")
    st.stop()

lista_equipes = sorted(df_global["EQUIPE"].dropna().astype(str).unique())
if not lista_equipes:
    st.error("Nenhuma equipe encontrada na base.")
    st.stop()


# ---------------------------------------------------------
# SIDEBAR – ESCOLHA DA EQUIPE E PERÍODO
# ---------------------------------------------------------
st.sidebar.title("Filtros da visão por equipe")

equipe_sel = st.sidebar.selectbox("Equipe", lista_equipes)

# Filtra base pela equipe escolhida
df = df_global[df_global["EQUIPE"] == equipe_sel].copy()

if df.empty:
    st.warning(f"Não há registros para a equipe **{equipe_sel}**.")
    st.stop()

# Cabeçalho com logo + título (depois de saber a equipe)
col_logo, col_title = st.columns([1, 4])
with col_logo:
    try:
        st.image("logo_mr.png", width=160)
    except Exception:
        st.write("")
with col_title:
    st.title("🧩 Funil de Vendas – Visão por Equipe")
    st.caption(
        f"Equipe selecionada: **{equipe_sel}** • "
        "Produtividade, funil de análises → aprovações → vendas e previsibilidade."
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


def obter_vendas_unicas(df_scope: pd.DataFrame) -> pd.DataFrame:
    """
    Uma venda por cliente (último status).
    """
    if df_scope.empty:
        return df_scope.copy()

    s = df_scope["STATUS_BASE"].fillna("").astype(str).str.upper()
    df_v = df_scope[s.isin(["VENDA GERADA", "VENDA INFORMADA"])].copy()
    if df_v.empty:
        return df_v

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

    df_v = df_v.sort_values("DIA")
    df_ult = df_v.groupby("CHAVE_CLIENTE").tail(1).copy()
    return df_ult


def format_currency(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------
# DATA_BASE (MÊS COMERCIAL) PARA ESSA EQUIPE
# ---------------------------------------------------------
col_data_base_original = None
for cand in [
    "DATA_BASE",
    "DATA BASE",
    "DATA BASE MÊS",
    "DATA BASE MES",
    "MÊS COMERCIAL",
    "MES COMERCIAL",
]:
    if cand in df.columns:
        col_data_base_original = cand
        break

if col_data_base_original is not None:
    serie_bruta = df[col_data_base_original]
    dt_base = pd.to_datetime(serie_bruta, dayfirst=True, errors="coerce")
    if dt_base.isna().all():
        dt_base = pd.to_datetime(serie_bruta, errors="coerce")
    if dt_base.isna().all():
        df["DATA_BASE"] = pd.to_datetime(df["DIA"], errors="coerce")
    else:
        df["DATA_BASE"] = dt_base
else:
    df["DATA_BASE"] = pd.to_datetime(df["DIA"], errors="coerce")

dias_validos = df["DIA"].dropna()
bases_validas = df["DATA_BASE"].dropna()

# limites de data para a equipe
hoje = date.today()
if dias_validos.empty:
    data_min_mov = hoje - timedelta(days=30)
    data_max_mov = hoje
else:
    data_min_mov = dias_validos.min().date()
    data_max_mov = dias_validos.max().date()

# permitir datas futuras (até 1 ano)
max_futuro = max(data_max_mov, hoje) + timedelta(days=365)


# ---------------------------------------------------------
# PERÍODO – DATA DE MOVIMENTAÇÃO
# ---------------------------------------------------------
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

mask_mov = (df["DIA"].dt.date >= data_ini_mov) & (df["DIA"].dt.date <= data_fim_mov)
df_periodo = df[mask_mov].copy()

st.caption(
    f"Equipe: **{equipe_sel}** • Período (movimentação): "
    f"**{data_ini_mov.strftime('%d/%m/%Y')}** até **{data_fim_mov.strftime('%d/%m/%Y')}**."
)

if df_periodo.empty:
    st.warning("Nenhum registro para essa equipe no período selecionado.")
    st.stop()


# ---------------------------------------------------------
# FUNIL DA EQUIPE – PERÍODO
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

# --------- LEADS DO PERÍODO (CRM – OBRIGATORIAMENTE DA EQUIPE) ---------
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

    # PROCURAR UMA COLUNA DE EQUIPE NO CRM
    equipe_col = None
    cols_lower = {c.lower(): c for c in df_leads_use.columns}
    for nome in ["equipe", "nome_equipe", "time", "equipe_nome"]:
        if nome in cols_lower:
            equipe_col = cols_lower[nome]
            break

    if equipe_col is not None:
        mask_periodo_leads = (
            (df_leads_use["data_captura_date"] >= data_ini_mov)
            & (df_leads_use["data_captura_date"] <= data_fim_mov)
        )
        mask_equipe_leads = df_leads_use[equipe_col].astype(str) == str(equipe_sel)
        df_leads_periodo = df_leads_use[mask_periodo_leads & mask_equipe_leads].copy()

        total_leads_periodo = len(df_leads_periodo)

        if total_leads_periodo > 0:
            conv_leads_analise_pct = (
                analises_em / total_leads_periodo * 100 if analises_em > 0 else 0.0
            )
            leads_por_analise = (
                total_leads_periodo / analises_em if analises_em > 0 else None
            )
    else:
        st.info(
            "Os leads ainda não estão marcados por equipe no CRM (coluna de equipe "
            "não encontrada no df_leads). Por isso, os indicadores de leads da equipe "
            "não foram calculados para evitar misturar com a imobiliária toda."
        )

# -------------------------------------------------------------------
st.markdown("## 🧭 Funil da Equipe – Período Selecionado")

# Linha de métricas de LEADS x ANÁLISE
lc1, lc2, lc3 = st.columns(3)
with lc1:
    st.metric(
        "Leads da equipe (CRM – período)",
        total_leads_periodo if total_leads_periodo is not None else "—",
    )
with lc2:
    if conv_leads_analise_pct is not None:
        st.metric(
            "Leads → Análises (só EM)",
            f"{conv_leads_analise_pct:.1f}%",
            help="Percentual de leads da equipe, no período, que viraram análise (só EM ANÁLISE).",
        )
    else:
        st.metric("Leads → Análises (só EM)", "—")
with lc3:
    if leads_por_analise is not None:
        st.metric(
            "Relação leads/análise (só EM)",
            f"{leads_por_analise:.1f} leads/análise",
            help="Em média, quantos leads essa equipe precisa para sair 1 análise (só EM ANÁLISE).",
        )
    else:
        st.metric("Relação leads/análise (só EM)", "—")

# Métricas clássicas do funil da equipe
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
    st.metric("Taxa Aprov./Análises", f"{taxa_aprov_analise:.1f}%")
with c8:
    st.metric("Taxa Vendas/Análises", f"{taxa_venda_analise:.1f}%")

c9, c10 = st.columns(2)
with c9:
    st.metric("Taxa Vendas/Aprovações", f"{taxa_venda_aprov:.1f}%")
with c10:
    st.metric(
        "IPC do período (vendas/corretor)",
        f"{ipc_periodo:.2f}" if ipc_periodo is not None else "—",
        help="Vendas únicas por corretor dessa equipe no período.",
    )

st.markdown("---")


# ---------------------------------------------------------
# PRODUTIVIDADE DA EQUIPE – PERÍODO
# ---------------------------------------------------------
st.markdown("## 👥 Produtividade da equipe – período selecionado")

if corretores_ativos_periodo == 0:
    st.info("Nenhum corretor dessa equipe teve movimentação no período.")
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

    c11, c12, c13, c14 = st.columns(4)
    with c11:
        st.metric("Corretores ativos (período)", corretores_ativos_periodo)
    with c12:
        st.metric(
            "% equipe produtiva (período)",
            f"{equipe_produtiva_pct:.1f}%",
            help="Corretor produtivo = pelo menos 1 venda única no período.",
        )
    with c13:
        st.metric("Vendas (período – únicas)", vendas)
    with c14:
        st.metric(
            "IPC período (vendas/corretor)",
            f"{ipc_periodo:.2f}" if ipc_periodo is not None else "—",
        )

st.markdown("---")


# ---------------------------------------------------------
# HISTÓRICO 3 MESES – DATA_BASE (EQUIPE)
# ---------------------------------------------------------
st.markdown("## 📈 Funil histórico da equipe – últimos 3 meses (DATA BASE)")

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
            f"Essa equipe não possui registros nos últimos 3 meses de DATA BASE "
            f"(de {inicio_3m.date().strftime('%d/%m/%Y')} "
            f"até {data_ref_base.date().strftime('%d/%m/%Y')})."
        )
    else:
        status_3m = df_3m["STATUS_BASE"].fillna("").astype(str).str.upper()

        analises_3m = conta_analises_base(status_3m)
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
            f"Equipe **{equipe_sel}** • Janela (DATA BASE): "
            f"{inicio_3m.date().strftime('%d/%m/%Y')} a {data_ref_base.date().strftime('%d/%m/%Y')}."
        )

        st.markdown("### 🎯 Planejamento da equipe com base nos últimos 3 meses")

        meta_vendas = st.number_input(
            "Meta de vendas da equipe para o próximo período",
            min_value=0,
            step=1,
            value=int(vendas_3m / 3) if vendas_3m > 0 else 5,
            help="Use a meta de vendas da equipe (mês/período desejado).",
        )

        if meta_vendas > 0 and vendas_3m > 0:
            analises_necessarias = int(np.ceil(analises_por_venda * meta_vendas))
            aprovacoes_necessarias = int(np.ceil(aprovacoes_por_venda * meta_vendas))

            c23, c24, c25 = st.columns(3)
            with c23:
                st.metric("Meta de vendas (equipe)", meta_vendas)
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

            st.caption(
                "Cálculos baseados no funil real da equipe nos últimos 3 meses "
                "(não é teoria, é o histórico dela)."
            )
        elif meta_vendas > 0 and vendas_3m == 0:
            st.info(
                "Ainda não há vendas dessa equipe nos últimos 3 meses para calcular "
                "a previsibilidade do funil."
            )

        # -------------------------------------------------
        # GRÁFICO DE LINHAS – META x REAL (EQUIPE)
        # -------------------------------------------------
        if meta_vendas > 0 and vendas_3m > 0 and not df_periodo.empty:
            st.markdown("### 📊 Acompanhamento da meta da equipe no período selecionado")

            indicador = st.selectbox(
                "Indicador para comparar com a meta",
                ["Análises", "Aprovações", "Vendas"],
            )

            # eixo de dias: de data_ini_mov até data_fim_mov (inclui datas futuras)
            dr = pd.date_range(start=data_ini_mov, end=data_fim_mov, freq="D")
            dias_periodo = [d.date() for d in dr]

            if len(dias_periodo) == 0:
                st.info("Não há datas válidas no período para montar o gráfico.")
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
                elif indicador == "Aprovações":
                    df_temp = df_periodo[
                        df_periodo["STATUS_BASE"]
                        .fillna("")
                        .astype(str)
                        .str.upper()
                        == "APROVADO"
                    ].copy()
                    total_meta = aprovacoes_necessarias
                else:
                    df_temp = obter_vendas_unicas(df_periodo).copy()
                    total_meta = meta_vendas

                if df_temp.empty or total_meta == 0:
                    st.info(
                        "Não há dados suficientes ou a meta está zerada para o indicador escolhido."
                    )
                else:
                    df_temp["DIA_DATA"] = pd.to_datetime(df_temp["DIA"]).dt.date
                    cont_por_dia = (
                        df_temp.groupby("DIA_DATA")
                        .size()
                        .reindex(dias_periodo, fill_value=0)
                    )

                    # linha Real acumulada
                    df_line["Real"] = cont_por_dia.values
                    df_line["Real"] = df_line["Real"].cumsum()

                    # corta a linha Real depois do dia de hoje
                    hoje_date = hoje
                    limite_real = min(hoje_date, data_fim_mov)
                    mask_future = df_line.index.date > limite_real
                    df_line.loc[mask_future, "Real"] = np.nan

                    # linha Meta até o fim do período
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

                    # ponto marcando o dia de hoje (se estiver no período)
                    hoje_dentro = (hoje_date >= data_ini_mov) and (hoje_date <= data_fim_mov)
                    if hoje_dentro:
                        df_real_reset = df_line.reset_index()
                        df_real_hoje = df_real_reset[
                            df_real_reset["DIA"].dt.date == limite_real
                        ]
                        if not df_real_hoje.empty:
                            ponto_hoje = (
                                alt.Chart(df_real_hoje)
                                .mark_point(size=80)
                                .encode(x="DIA:T", y="Real:Q")
                            )
                            chart = chart + ponto_hoje

                    st.altair_chart(chart, use_container_width=True)
                    st.caption(
                        "Linha **Real** = indicador acumulado da equipe, parando no **dia de hoje**. "
                        "Linha **Meta** = ritmo necessário até a **data final escolhida** "
                        "para bater a meta da equipe."
                    )
