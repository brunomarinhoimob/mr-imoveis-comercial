import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import date

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
        "aprovações → vendas e previsibilidade a partir do funil do período selecionado pela DATA BASE."
    )


# ---------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------
def mes_ano_ptbr_para_date(texto: str):
    """
    Converte 'novembro 2025' -> date(2025, 11, 1).
    Se não conseguir, retorna NaT.
    """
    if not isinstance(texto, str):
        return pd.NaT

    t = texto.strip().lower()
    if not t:
        return pd.NaT

    partes = t.split()
    if len(partes) != 2:
        return pd.NaT

    mes_nome, ano_str = partes[0], partes[1]

    mapa_meses = {
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

    mes = mapa_meses.get(mes_nome)
    if mes is None:
        return pd.NaT

    try:
        ano = int(ano_str)
    except Exception:
        return pd.NaT

    try:
        return date(ano, mes, 1)
    except Exception:
        return pd.NaT


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
    status_final_map: pd.Series | None = None,
) -> pd.DataFrame:
    """
    Retorna uma venda por cliente (último status).
    Se tiver VENDA INFORMADA e depois VENDA GERADA, fica só a GERADA.

    Se status_final_map for informado (CHAVE_CLIENTE -> STATUS_FINAL_CLIENTE),
    remove clientes cujo último status global seja DESISTIU.
    """
    if df_scope.empty:
        return df_scope.copy()

    if status_venda is None:
        status_venda = ["VENDA GERADA", "VENDA INFORMADA"]

    s = df_scope["STATUS_BASE"].fillna("").astype(str).str.upper()
    df_v = df_scope[s.isin(status_venda)].copy()
    if df_v.empty:
        return df_v

    # Garante colunas de cliente / chave
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

    if "CHAVE_CLIENTE" not in df_v.columns:
        df_v["CHAVE_CLIENTE"] = (
            df_v["NOME_CLIENTE_BASE"]
            .fillna("NÃO INFORMADO")
            .astype(str)
            .str.upper()
            .str.strip()
            + " | "
            + df_v["CPF_CLIENTE_BASE"].fillna("").astype(str).str.strip()
        )

    # 👇 NOVO: aplica regra global do DESISTIU, se mapa foi passado
    if status_final_map is not None:
        df_v = df_v.merge(
            status_final_map,
            on="CHAVE_CLIENTE",
            how="left",
        )
        df_v = df_v[df_v["STATUS_FINAL_CLIENTE"] != "DESISTIU"]

    if df_v.empty:
        return df_v

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

# DIA em datetime
df["DIA"] = pd.to_datetime(df.get("DIA"), errors="coerce")

# 🔴 FORÇA O USO DA COLUNA "DATA BASE" DA PLANILHA
if "DATA BASE" in df.columns:
    base_raw = df["DATA BASE"].astype(str).str.strip()
    # Converte textos tipo "novembro 2025" em date(2025, 11, 1)
    df["DATA_BASE"] = base_raw.apply(mes_ano_ptbr_para_date)
    # Label para o seletor: mm/AAAA (11/2025, 12/2025, ...)
    df["DATA_BASE_LABEL"] = df["DATA_BASE"].apply(
        lambda d: d.strftime("%m/%Y") if pd.notnull(d) else ""
    )
else:
    # Fallback: usa DIA mesmo (não é o ideal, mas garante que funciona)
    df["DATA_BASE"] = df["DIA"]
    df["DATA_BASE_LABEL"] = df["DIA"].apply(
        lambda d: d.strftime("%m/%Y") if pd.notnull(d) else ""
    )

# 👇 NOVO: STATUS FINAL GLOBAL DO CLIENTE (HISTÓRICO COMPLETO)
# Usa CHAVE_CLIENTE que já vem do carregar_dados_planilha
df_ordenado_global = df.sort_values("DIA")
status_final_por_cliente = (
    df_ordenado_global.groupby("CHAVE_CLIENTE")["STATUS_BASE"].last().fillna("")
)
status_final_por_cliente.name = "STATUS_FINAL_CLIENTE"


# ---------------------------------------------------------
# SIDEBAR – APENAS SELETOR DE DATA BASE + TIPO DE VENDA
# ---------------------------------------------------------
st.sidebar.title("Filtros da visão imobiliária")

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
    bases_selecionadas = opcoes_bases

df_periodo = df[df["DATA_BASE_LABEL"].isin(bases_selecionadas)].copy()

# Tipo de venda
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

if df_periodo.empty:
    st.warning("Nenhum registro encontrado para o período selecionado pela DATA BASE.")
    st.stop()


# ---------------------------------------------------------
# DEFININDO O INTERVALO DE DIAS A PARTIR DA DATA BASE
# (mínimo e máximo da coluna DIA dentro das bases selecionadas)
# ---------------------------------------------------------
dias_sel = df_periodo["DIA"].dropna()
if not dias_sel.empty:
    data_ini_mov = dias_sel.min().date()
    data_fim_mov = dias_sel.max().date()
else:
    hoje = date.today()
    data_ini_mov = hoje
    data_fim_mov = hoje

# Texto da data base
if len(bases_selecionadas) == 1:
    base_str = bases_selecionadas[0]
else:
    base_str = f"{bases_selecionadas[0]} até {bases_selecionadas[-1]}"

st.caption(
    f"DATA BASE: **{base_str}** • "
    f"Dias: **{data_ini_mov.strftime('%d/%m/%Y')}** até **{data_fim_mov.strftime('%d/%m/%Y')}** • "
    f"Vendas consideradas no funil: **{desc_venda}**."
)


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
    status_final_map=status_final_por_cliente,  # 👈 aplica regra DESISTIU
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

# BLOCO PRINCIPAL DO FUNIL – KPIs
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
        f"Período considerado (DIA dentro da DATA BASE selecionada): "
        f"{data_ini_mov.strftime('%d/%m/%Y')} até {data_fim_mov.strftime('%d/%m/%Y')}."
    )

st.markdown("---")


# ---------------------------------------------------------
# PLANEJAMENTO BASEADO NO FUNIL DO PERÍODO (CONECTADO À DATA BASE)
# ---------------------------------------------------------
st.markdown("## 🎯 Planejamento com base no funil do período (DATA BASE selecionada)")

analises_necessarias = 0
aprovacoes_necessarias = 0
meta_vendas = 0

if vendas > 0:
    analises_por_venda = analises_em / vendas if analises_em > 0 else 0.0
    aprovacoes_por_venda = aprovacoes / vendas if aprovacoes > 0 else 0.0

    meta_vendas = st.number_input(
        "Meta de vendas (imobiliária) para o próximo período",
        min_value=0,
        step=1,
        value=int(vendas),
    )

    if meta_vendas > 0:
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

        st.caption(
            "Cálculos feitos com base no funil filtrado pela DATA BASE acima. "
            "Quando você alterar a DATA BASE, os dias considerados e as quantidades necessárias se recalculam automaticamente."
        )

        # -------------------------------------------------
        # GRÁFICO – META x REAL COM INTERVALO LIVRE (IMOBILIÁRIA)
        # -------------------------------------------------
        if not df_periodo.empty:
            st.markdown("### 📊 Acompanhamento da meta da imobiliária no intervalo escolhido")

            indicador = st.selectbox(
                "Indicador para comparar com a meta",
                ["Análises", "Aprovações", "Vendas"],
            )

            periodo_meta = st.date_input(
                "Período do acompanhamento da meta",
                value=(data_ini_mov, data_fim_mov),
            )

            if isinstance(periodo_meta, (tuple, list)) and len(periodo_meta) == 2:
                data_ini_sel, data_fim_sel = periodo_meta
            else:
                data_ini_sel = data_ini_mov
                data_fim_sel = data_fim_mov

            if data_ini_sel > data_fim_sel:
                st.error("A data inicial do acompanhamento não pode ser maior que a data final.")
            else:
                dr = pd.date_range(start=data_ini_sel, end=data_fim_sel, freq="D")
                dias_meta = [d.date() for d in dr]

                if len(dias_meta) == 0:
                    st.info("Não há datas válidas no período para montar o gráfico.")
                else:
                    df_periodo["DIA_DATA"] = pd.to_datetime(df_periodo["DIA"]).dt.date
                    df_range = df_periodo[
                        (df_periodo["DIA_DATA"] >= data_ini_sel)
                        & (df_periodo["DIA_DATA"] <= data_fim_sel)
                    ].copy()

                    if indicador == "Análises":
                        df_temp = df_range[
                            df_range["STATUS_BASE"]
                            .fillna("")
                            .astype(str)
                            .str.upper()
                            == "EM ANÁLISE"
                        ].copy()
                        total_meta = analises_necessarias
                    elif indicador == "Aprovações":
                        df_temp = df_range[
                            df_range["STATUS_BASE"]
                            .fillna("")
                            .astype(str)
                            .str.upper()
                            == "APROVADO"
                        ].copy()
                        total_meta = aprovacoes_necessarias
                    else:
                        df_temp = obter_vendas_unicas(
                            df_range,
                            status_venda=status_venda_considerado,
                            status_final_map=status_final_por_cliente,  # 👈 regra DESISTIU também no gráfico
                        ).copy()
                        total_meta = meta_vendas

                    if df_temp.empty or total_meta == 0:
                        st.info(
                            "Não há dados suficientes nesse intervalo "
                            "ou a meta está zerada para o indicador escolhido."
                        )
                    else:
                        df_temp["DIA_DATA"] = pd.to_datetime(df_temp["DIA"]).dt.date
                        cont_por_dia = (
                            df_temp.groupby("DIA_DATA")
                            .size()
                            .reindex(dias_meta, fill_value=0)
                        )

                        idx = pd.to_datetime(dias_meta)
                        df_line = pd.DataFrame(index=idx)
                        df_line.index.name = "DIA"

                        df_line["Real"] = cont_por_dia.values
                        df_line["Real"] = df_line["Real"].cumsum()

                        # Linha REAL para no último dia com movimento
                        ultimo_mov = df_temp["DIA_DATA"].max()
                        if pd.notnull(ultimo_mov):
                            mask_future_real = df_line.index.date > ultimo_mov
                            df_line.loc[mask_future_real, "Real"] = np.nan

                        # Linha META: linear de 0 até total_meta no intervalo selecionado
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
                                x=alt.X("DIA:T", title="Dia"),
                                y=alt.Y("Valor:Q", title="Quantidade acumulada"),
                                color=alt.Color("Série:N", title=""),
                            )
                            .properties(height=320)
                        )

                        st.altair_chart(chart, use_container_width=True)
                        st.caption(
                            "Linha **Real** = indicador acumulado da imobiliária **apenas dentro do intervalo escolhido**, "
                            "parando no último dia com movimentação. "
                            "Linha **Meta** = ritmo necessário, do início ao fim do intervalo, "
                            "para atingir o total de análises/aprovações/vendas calculado com base no funil do período."
                        )

else:
    st.info(
        "Ainda não há vendas no período selecionado para projetar a quantidade de análises e aprovações. "
        "Ajuste o filtro de DATA BASE para um período com vendas."
    )
