import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import date, timedelta

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Painel de Vendas – MR Imóveis",
    page_icon="💰",
    layout="wide",
)

st.title("💰 Painel de Vendas – MR Imóveis")

st.caption(
    "Visão consolidada das vendas da imobiliária: VGV, ranking por equipe/corretor, "
    "evolução diária e mix por construtora/empreendimento."
)

# ---------------------------------------------------------
# CONFIG: LINK DA PLANILHA  (MESMO DO APP PRINCIPAL)
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
# CARREGAR E PREPARAR DADOS (PLANILHA)
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

    # CONSTRUTORA / EMPREENDIMENTO (para mix de vendas)
    possiveis_construtora = ["CONSTRUTORA", "INCORPORADORA"]
    possiveis_empreend = ["EMPREENDIMENTO", "PRODUTO", "IMÓVEL", "IMOVEL"]

    col_construtora = None
    for c in possiveis_construtora:
        if c in df.columns:
            col_construtora = c
            break

    col_empreend = None
    for c in possiveis_empreend:
        if c in df.columns:
            col_empreend = c
            break

    if col_construtora is None:
        df["CONSTRUTORA_BASE"] = "NÃO INFORMADO"
    else:
        df["CONSTRUTORA_BASE"] = (
            df[col_construtora]
            .fillna("NÃO INFORMADO")
            .astype(str)
            .str.upper()
            .str.strip()
        )

    if col_empreend is None:
        df["EMPREENDIMENTO_BASE"] = "NÃO INFORMADO"
    else:
        df["EMPREENDIMENTO_BASE"] = (
            df[col_empreend]
            .fillna("NÃO INFORMADO")
            .astype(str)
            .str.upper()
            .str.strip()
        )

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

    # NOME / CPF BASE PARA CHAVE DO CLIENTE (UNIFICAR VENDAS)
    possiveis_nome = ["NOME", "CLIENTE", "NOME CLIENTE", "NOME DO CLIENTE"]
    possiveis_cpf = ["CPF", "CPF CLIENTE", "CPF DO CLIENTE"]

    col_nome = None
    for c in possiveis_nome:
        if c in df.columns:
            col_nome = c
            break

    col_cpf = None
    for c in possiveis_cpf:
        if c in df.columns:
            col_cpf = c
            break

    if col_nome is None:
        df["NOME_CLIENTE_BASE"] = "NÃO INFORMADO"
    else:
        df["NOME_CLIENTE_BASE"] = (
            df[col_nome]
            .fillna("NÃO INFORMADO")
            .astype(str)
            .str.upper()
            .str.strip()
        )

    if col_cpf is None:
        df["CPF_CLIENTE_BASE"] = ""
    else:
        df["CPF_CLIENTE_BASE"] = (
            df[col_cpf]
            .fillna("")
            .astype(str)
            .str.replace(r"\D", "", regex=True)
        )

    return df


df = carregar_dados()

if df.empty:
    st.error("Não foi possível carregar dados da planilha. Verifique o link/gid.")
    st.stop()

# ---------------------------------------------------------
# LEADS DO SUPREMO (APROVEITA DF_LEADS DO app principal, SE EXISTIR)
# ---------------------------------------------------------
df_leads = st.session_state.get("df_leads", pd.DataFrame())


# ---------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------
def conta_vendas(s):
    return s.isin(["VENDA GERADA", "VENDA INFORMADA"]).sum()


def conta_aprovacoes(s):
    return (s == "APROVADO").sum()


def obter_vendas_unicas(df_scope: pd.DataFrame) -> pd.DataFrame:
    """
    Retorna apenas UMA venda por cliente (nome + CPF), usando o último status.
    Se existir VENDA INFORMADA e depois VENDA GERADA, fica só a VENDA GERADA.
    """
    df_v = df_scope[df_scope["STATUS_BASE"].isin(["VENDA GERADA", "VENDA INFORMADA"])].copy()
    if df_v.empty:
        return df_v

    df_v["CHAVE_CLIENTE"] = (
        df_v["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO")
        + " | "
        + df_v["CPF_CLIENTE_BASE"].fillna("")
    )

    # Ordena cronologicamente e pega SEMPRE a última linha de cada cliente
    df_v = df_v.sort_values("DIA")
    df_v_ult = df_v.groupby("CHAVE_CLIENTE").tail(1)

    return df_v_ult


# ---------------------------------------------------------
# SIDEBAR – FILTROS (PAINEL DO GESTOR)
# ---------------------------------------------------------
st.sidebar.title("Filtros 🔎")

dias_validos = pd.Series(df["DIA"].dropna())

if not dias_validos.empty:
    data_min = dias_validos.min()
    data_max = dias_validos.max()
else:
    hoje = date.today()
    data_max = hoje
    data_min = hoje - timedelta(days=30)

# Janela padrão: últimos 30 dias até a última data da base
data_ini_default = max(data_min, data_max - timedelta(days=30))

periodo = st.sidebar.date_input(
    "Período das vendas",
    value=(data_ini_default, data_max),
    min_value=data_min,
    max_value=data_max,
)

if isinstance(periodo, tuple):
    data_ini, data_fim = periodo
else:
    data_ini, data_fim = data_ini_default, data_max

# Filtro de equipe
lista_equipes = sorted(df["EQUIPE"].dropna().unique())
equipe_sel = st.sidebar.selectbox("Equipe", ["Todas"] + lista_equipes)

# Filtro de corretor depende da equipe
if equipe_sel == "Todas":
    base_corretor = df
else:
    base_corretor = df[df["EQUIPE"] == equipe_sel]

lista_corretor = sorted(base_corretor["CORRETOR"].dropna().unique())
corretor_sel = st.sidebar.selectbox("Corretor", ["Todos"] + lista_corretor)

# Meta de vendas (para % de atingimento)
meta_vendas = st.sidebar.number_input(
    "Meta de vendas (qtde) para o período",
    min_value=0,
    value=10,
    step=1,
)


# ---------------------------------------------------------
# APLICA FILTROS PRINCIPAIS
# ---------------------------------------------------------
df_periodo = df.copy()

# Período
dia_series_all = limpar_para_data(df_periodo["DIA"])
mask_data = (dia_series_all >= data_ini) & (dia_series_all <= data_fim)
df_periodo = df_periodo[mask_data]

# Equipe
if equipe_sel != "Todas":
    df_periodo = df_periodo[df_periodo["EQUIPE"] == equipe_sel]

# Corretor
if corretor_sel != "Todos":
    df_periodo = df_periodo[df_periodo["CORRETOR"] == corretor_sel]

registros_filtrados = len(df_periodo)

st.caption(
    f"Período: **{data_ini.strftime('%d/%m/%Y')}** até **{data_fim.strftime('%d/%m/%Y')}** • "
    f"Registros na base: **{registros_filtrados}**"
    + (f" • Equipe: **{equipe_sel}**" if equipe_sel != "Todas" else "")
    + (f" • Corretor: **{corretor_sel}**" if corretor_sel != "Todos" else "")
)

if df_periodo.empty:
    st.warning("Não há registros para os filtros selecionados.")
    st.stop()

# ---------------------------------------------------------
# FILTRA SÓ VENDAS PARA OS KPIs (VENDAS ÚNICAS POR CLIENTE)
# ---------------------------------------------------------
df_vendas = obter_vendas_unicas(df_periodo)

qtd_vendas = len(df_vendas)
vgv_total = df_vendas["VGV"].sum()
ticket_medio = vgv_total / qtd_vendas if qtd_vendas > 0 else 0

# Aprovações no período (pra taxa aprovação -> venda)
qtd_aprovacoes = conta_aprovacoes(df_periodo["STATUS_BASE"])
taxa_venda_aprov = (qtd_vendas / qtd_aprovacoes * 100) if qtd_aprovacoes > 0 else 0

# Leads do CRM no período (se houver)
total_leads_periodo = None
if not df_leads.empty and "data_captura" in df_leads.columns:
    df_leads_use = df_leads.dropna(subset=["data_captura"]).copy()
    df_leads_use["data_captura"] = pd.to_datetime(df_leads_use["data_captura"], errors="coerce")
    df_leads_use["data_captura_date"] = df_leads_use["data_captura"].dt.date

    mask_leads_periodo = (
        (df_leads_use["data_captura_date"] >= data_ini)
        & (df_leads_use["data_captura_date"] <= data_fim)
    )

    # Leads gerais da imobiliária dentro do período
    df_leads_periodo = df_leads_use[mask_leads_periodo].copy()
    total_leads_periodo = len(df_leads_periodo)

leads_por_venda = None
if total_leads_periodo is not None and qtd_vendas > 0:
    leads_por_venda = total_leads_periodo / qtd_vendas

# % meta atingida
perc_meta = (qtd_vendas / meta_vendas * 100) if meta_vendas > 0 else 0

# ---------------------------------------------------------
# KPIs PRINCIPAIS (CARDS)
# ---------------------------------------------------------
st.markdown("## 🏅 Placar de Vendas do Período")

c1, c2, c3, c4, c5, c6 = st.columns(6)

with c1:
    st.metric("Vendas no período", qtd_vendas)

with c2:
    st.metric(
        "VGV Total",
        f"R$ {vgv_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
    )

with c3:
    st.metric(
        "Ticket médio",
        f"R$ {ticket_medio:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
    )

with c4:
    st.metric("Meta de vendas (qtde)", meta_vendas)

with c5:
    st.metric("Meta atingida (%)", f"{perc_meta:.1f}%")

with c6:
    st.metric("Taxa Vendas/Aprovações", f"{taxa_venda_aprov:.1f}%")

c7, c8 = st.columns(2)

with c7:
    if total_leads_periodo is None:
        st.metric("Leads (CRM) no período", "-")
    else:
        st.metric("Leads (CRM) no período", total_leads_periodo)

with c8:
    if leads_por_venda is None:
        st.metric("Leads por venda (CRM)", "-")
    else:
        st.metric("Leads por venda (CRM)", f"{leads_por_venda:.1f}")


# ---------------------------------------------------------
# GRÁFICO DE EVOLUÇÃO DIÁRIA (VGV E VENDAS)
# ---------------------------------------------------------
st.markdown("---")
st.markdown("## 📈 Evolução diária das vendas")

if df_vendas.empty:
    st.info("Ainda não há vendas no período selecionado.")
else:
    # Agrupa por dia
    df_vendas_dia = (
        df_vendas.groupby("DIA")
        .agg(
            VGV_DIA=("VGV", "sum"),
            QTD_VENDAS=("STATUS_BASE", "count"),
        )
        .reset_index()
        .sort_values("DIA")
    )

    df_vendas_dia["DIA_STR"] = pd.to_datetime(df_vendas_dia["DIA"]).dt.strftime("%d/%m")

    # VGV diário (barras)
    st.markdown("### 💵 VGV por dia")
    chart_vgv_dia = (
        alt.Chart(df_vendas_dia)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("DIA_STR:N", title="Dia"),
            y=alt.Y("VGV_DIA:Q", title="VGV do dia (R$)"),
            tooltip=[
                alt.Tooltip("DIA_STR:N", title="Dia"),
                alt.Tooltip("VGV_DIA:Q", title="VGV do dia", format=",.2f"),
                alt.Tooltip("QTD_VENDAS:Q", title="Qtde de vendas"),
            ],
        )
        .properties(height=300)
    )
    st.altair_chart(chart_vgv_dia, use_container_width=True)

    # VGV acumulado (linha)
    df_vendas_dia["VGV_ACUM"] = df_vendas_dia["VGV_DIA"].cumsum()

    st.markdown("### 📊 VGV acumulado no período")
    chart_vgv_acum = (
        alt.Chart(df_vendas_dia)
        .mark_line(point=True)
        .encode(
            x=alt.X("DIA_STR:N", title="Dia"),
            y=alt.Y("VGV_ACUM:Q", title="VGV acumulado (R$)"),
            tooltip=[
                alt.Tooltip("DIA_STR:N", title="Dia"),
                alt.Tooltip("VGV_ACUM:Q", title="VGV acumulado", format=",.2f"),
            ],
        )
        .properties(height=300)
    )
    st.altair_chart(chart_vgv_acum, use_container_width=True)


# ---------------------------------------------------------
# RANKING POR EQUIPE
# ---------------------------------------------------------
st.markdown("---")
st.markdown("## 👥 Ranking de Vendas por Equipe")

df_vendas_eq = df_vendas.copy()

if df_vendas_eq.empty:
    st.info("Não há vendas para montar o ranking de equipes neste período.")
else:
    rank_eq = (
        df_vendas_eq.groupby("EQUIPE")
        .agg(
            VENDAS=("STATUS_BASE", "count"),
            VGV=("VGV", "sum"),
        )
        .reset_index()
    )

    rank_eq["TICKET_MEDIO"] = np.where(
        rank_eq["VENDAS"] > 0,
        rank_eq["VGV"] / rank_eq["VENDAS"],
        0,
    )

    if vgv_total > 0:
        rank_eq["%_VGV_IMOB"] = rank_eq["VGV"] / vgv_total * 100
    else:
        rank_eq["%_VGV_IMOB"] = 0.0

    rank_eq = rank_eq.sort_values(["VENDAS", "VGV"], ascending=False)

    st.dataframe(
        rank_eq.style.format(
            {
                "VGV": "R$ {:,.2f}".format,
                "TICKET_MEDIO": "R$ {:,.2f}".format,
                "%_VGV_IMOB": "{:.1f}%".format,
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### 💰 VGV por equipe")
    chart_eq_vgv = (
        alt.Chart(rank_eq)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("VGV:Q", title="VGV (R$)"),
            y=alt.Y("EQUIPE:N", sort="-x", title="Equipe"),
            tooltip=[
                "EQUIPE",
                alt.Tooltip("VENDAS:Q", title="Vendas"),
                alt.Tooltip("VGV:Q", title="VGV", format=",.2f"),
                alt.Tooltip("TICKET_MEDIO:Q", title="Ticket médio", format=",.2f"),
                alt.Tooltip("%_VGV_IMOB:Q", title="% do VGV da imob", format=".1f"),
            ],
        )
        .properties(height=400)
    )
    st.altair_chart(chart_eq_vgv, use_container_width=True)


# ---------------------------------------------------------
# RANKING POR CORRETOR
# ---------------------------------------------------------
st.markdown("---")
st.markdown("## 🧑‍💼 Ranking de Vendas por Corretor")

df_vendas_cor = df_vendas.copy()

if df_vendas_cor.empty:
    st.info("Não há vendas para montar o ranking de corretores neste período.")
else:
    rank_cor = (
        df_vendas_cor.groupby(["CORRETOR", "EQUIPE"])
        .agg(
            VENDAS=("STATUS_BASE", "count"),
            VGV=("VGV", "sum"),
        )
        .reset_index()
    )

    rank_cor["TICKET_MEDIO"] = np.where(
        rank_cor["VENDAS"] > 0,
        rank_cor["VGV"] / rank_cor["VENDAS"],
        0,
    )

    if vgv_total > 0:
        rank_cor["%_VGV_IMOB"] = rank_cor["VGV"] / vgv_total * 100
    else:
        rank_cor["%_VGV_IMOB"] = 0.0

    rank_cor = rank_cor.sort_values(["VGV", "VENDAS"], ascending=False)

    st.dataframe(
        rank_cor.style.format(
            {
                "VGV": "R$ {:,.2f}".format,
                "TICKET_MEDIO": "R$ {:,.2f}".format,
                "%_VGV_IMOB": "{:.1f}%".format,
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    # Top 10 para gráfico
    rank_cor_top = rank_cor.head(10).copy()
    rank_cor_top["CORRETOR_LABEL"] = (
        rank_cor_top["CORRETOR"].astype(str).str[:20] + " (" + rank_cor_top["EQUIPE"] + ")"
    )

    st.markdown("### 🏆 Top 10 corretores por VGV")
    chart_cor_vgv = (
        alt.Chart(rank_cor_top)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("VGV:Q", title="VGV (R$)"),
            y=alt.Y("CORRETOR_LABEL:N", sort="-x", title="Corretor (Equipe)"),
            tooltip=[
                "CORRETOR",
                "EQUIPE",
                alt.Tooltip("VENDAS:Q", title="Vendas"),
                alt.Tooltip("VGV:Q", title="VGV", format=",.2f"),
                alt.Tooltip("TICKET_MEDIO:Q", title="Ticket médio", format=",.2f"),
                alt.Tooltip("%_VGV_IMOB:Q", title="% do VGV da imob", format=".1f"),
            ],
        )
        .properties(height=400)
    )
    st.altair_chart(chart_cor_vgv, use_container_width=True)


# ---------------------------------------------------------
# MIX DE VENDAS (CONSTRUTORA / EMPREENDIMENTO)
# ---------------------------------------------------------
st.markdown("---")
st.markdown("## 🧱 Mix de Vendas (Construtora / Empreendimento)")

if df_vendas.empty:
    st.info("Sem vendas no período para mostrar o mix.")
else:
    c_mix1, c_mix2 = st.columns(2)

    with c_mix1:
        st.markdown("### Por Construtora")
        mix_const = (
            df_vendas.groupby("CONSTRUTORA_BASE")
            .agg(
                QTDE_VENDAS=("VGV", "size"),
                VGV=("VGV", "sum"),
            )
            .reset_index()
            .sort_values("VGV", ascending=False)
        )
        st.dataframe(
            mix_const.style.format(
                {
                    "VGV": "R$ {:,.2f}".format,
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    with c_mix2:
        st.markdown("### Por Empreendimento")
        mix_empr = (
            df_vendas.groupby("EMPREENDIMENTO_BASE")["VGV"]
            .sum()
            .reset_index()
            .sort_values("VGV", ascending=False)
            .head(15)
        )
        st.dataframe(
            mix_empr.style.format({"VGV": "R$ {:,.2f}".format}),
            use_container_width=True,
            hide_index=True,
        )


# ---------------------------------------------------------
# TABELA DETALHADA DE VENDAS (UMA LINHA POR CLIENTE)
# ---------------------------------------------------------
st.markdown("---")
st.markdown("## 📋 Detalhamento de Vendas (linha a linha)")

colunas_preferidas = [
    "DIA",
    "NOME_CLIENTE_BASE",
    "CPF_CLIENTE_BASE",
    "EQUIPE",
    "CORRETOR",
    "CONSTRUTORA_BASE",
    "EMPREENDIMENTO_BASE",
    "STATUS_BASE",
    "VGV",
]
colunas_existentes = [c for c in colunas_preferidas if c in df_vendas.columns]

df_tab = df_vendas[colunas_existentes].copy()

# Formata data
if "DIA" in df_tab.columns:
    df_tab["DIA"] = pd.to_datetime(df_tab["DIA"], errors="coerce").dt.strftime("%d/%m/%Y")

# Renomeia para ficar mais amigável
renomear = {
    "DIA": "Data",
    "NOME_CLIENTE_BASE": "Cliente",
    "CPF_CLIENTE_BASE": "CPF",
    "EQUIPE": "Equipe",
    "CORRETOR": "Corretor",
    "CONSTRUTORA_BASE": "Construtora",
    "EMPREENDIMENTO_BASE": "Empreendimento",
    "STATUS_BASE": "Status",
    "VGV": "VGV",
}
df_tab = df_tab.rename(columns=renomear)

# Ordena pela data mais recente
if "Data" in df_tab.columns:
    df_tab = df_tab.sort_values("Data", ascending=False)

st.dataframe(
    df_tab.style.format({"VGV": "R$ {:,.2f}".format}),
    use_container_width=True,
    hide_index=True,
)
