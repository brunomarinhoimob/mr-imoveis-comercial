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

# ---------------------------------------------------------
# CABEÇALHO COM LOGO + TÍTULO
# ---------------------------------------------------------
col_logo, col_title = st.columns([1, 4])
with col_logo:
    try:
        st.image("logo_mr.png", use_container_width=True)
    except Exception:
        st.write("")
with col_title:
    st.title("💰 Painel de Vendas – MR Imóveis")
    st.caption(
        "Visão consolidada das vendas da imobiliária: VGV, ranking por equipe/corretor, "
        "evolução diária e mix por construtora/empreendimento, já com a regra do DESISTIU aplicada."
    )

# ---------------------------------------------------------
# LINK DA PLANILHA
# ---------------------------------------------------------
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID_ANALISES = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ANALISES}"


def limpar_para_data(serie: pd.Series) -> pd.Series:
    dt = pd.to_datetime(serie, dayfirst=True, errors="coerce")
    return dt.dt.date


def mes_ano_ptbr_para_date(texto: str):
    """
    Converte strings tipo 'novembro 2025' -> date(2025, 11, 1).
    """
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


@st.cache_data(ttl=60)
def carregar_dados() -> pd.DataFrame:
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

    # CONSTRUTORA / EMPREENDIMENTO
    possiveis_construtora = ["CONSTRUTORA", "INCORPORADORA"]
    possiveis_empreend = ["EMPREENDIMENTO", "PRODUTO", "IMÓVEL", "IMOVEL"]

    col_construtora = next((c for c in possiveis_construtora if c in df.columns), None)
    col_empreend = next((c for c in possiveis_empreend if c in df.columns), None)

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

    # STATUS / SITUAÇÃO
    possiveis_cols_situacao = [
        "SITUAÇÃO",
        "SITUAÇÃO ATUAL",
        "STATUS",
        "SITUACAO",
        "SITUACAO ATUAL",
    ]
    col_situacao = next((c for c in possiveis_cols_situacao if c in df.columns), None)

    df["STATUS_BASE"] = ""
    if col_situacao:
        status_upper = df[col_situacao].fillna("").astype(str).str.upper()

        df.loc[status_upper.str.contains("EM ANÁLISE"), "STATUS_BASE"] = "EM ANÁLISE"
        df.loc[status_upper.str.contains("REANÁLISE"), "STATUS_BASE"] = "REANÁLISE"
        df.loc[status_upper.str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA GERADA"
        df.loc[status_upper.str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA INFORMADA"
        df.loc[status_upper.str.contains(r"\bAPROVAÇÃO\b"), "STATUS_BASE"] = "APROVADO"
        df.loc[status_upper.str.contains("DESIST", na=False), "STATUS_BASE"] = "DESISTIU"

    # OBSERVAÇÕES / VGV
    if "OBSERVAÇÕES" in df.columns:
        df["OBSERVACOES_RAW"] = (
            df["OBSERVAÇÕES"].fillna("").astype(str).str.strip()
        )
        df["VGV"] = pd.to_numeric(df["OBSERVAÇÕES"], errors="coerce").fillna(0.0)
    else:
        df["OBSERVACOES_RAW"] = ""
        df["VGV"] = 0.0

    # NOME / CPF
    possiveis_nome = ["NOME", "CLIENTE", "NOME CLIENTE", "NOME DO CLIENTE"]
    possiveis_cpf = ["CPF", "CPF CLIENTE", "CPF DO CLIENTE"]

    col_nome = next((c for c in possiveis_nome if c in df.columns), None)
    col_cpf = next((c for c in possiveis_cpf if c in df.columns), None)

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

    # Garante CHAVE_CLIENTE global
    df["CHAVE_CLIENTE"] = (
        df["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
        + " | "
        + df["CPF_CLIENTE_BASE"].fillna("").astype(str).str.strip()
    )

    return df


def format_currency(valor: float) -> str:
    return (
        f"R$ {valor:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def conta_aprovacoes(status_serie: pd.Series) -> int:
    if status_serie is None or status_serie.empty:
        return 0
    s = status_serie.fillna("").astype(str).str.upper()
    return s.str.contains(r"\bAPROVADO\b").sum()


def obter_vendas_unicas(
    df_scope: pd.DataFrame,
    status_vendas=None,
    status_final_map: pd.Series | None = None,
) -> pd.DataFrame:
    """
    Uma venda por cliente (último status dentro da lista status_vendas),
    considerando apenas registros cujo STATUS_BASE está em status_vendas
    E aplicando a regra global do DESISTIU via status_final_map.
    """
    if df_scope.empty:
        return df_scope.copy()

    if status_vendas is None:
        status_vendas = ["VENDA GERADA", "VENDA INFORMADA"]

    s = df_scope["STATUS_BASE"].fillna("").astype(str).str.upper()
    df_v = df_scope[s.isin(status_vendas)].copy()
    if df_v.empty:
        return df_v

    df_v["CHAVE_CLIENTE"] = (
        df_v["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
        + " | "
        + df_v["CPF_CLIENTE_BASE"].fillna("").astype(str).str.strip()
    )

    # Regra DESISTIU global: descarta clientes cujo status final seja DESISTIU
    if status_final_map is not None:
        df_v = df_v.merge(
            status_final_map,
            on="CHAVE_CLIENTE",
            how="left",
        )
        df_v = df_v[df_v["STATUS_FINAL_CLIENTE"] != "DESISTIU"]

    if df_v.empty:
        return df_v

    df_v = df_v.sort_values("DIA")
    df_ult = df_v.groupby("CHAVE_CLIENTE").tail(1).copy()
    return df_ult


# ---------------------------------------------------------
# CARREGA BASE
# ---------------------------------------------------------
df = carregar_dados()

if df.empty:
    st.error("Não foi possível carregar dados da planilha de vendas.")
    st.stop()

# Garante DIA como datetime para filtros
df["DIA"] = pd.to_datetime(df["DIA"], errors="coerce")

# DATA BASE (mês comercial)
if "DATA BASE" in df.columns:
    df["DATA_BASE"] = df["DATA BASE"].astype(str).apply(mes_ano_ptbr_para_date)
    df["DATA_BASE_LABEL"] = df["DATA_BASE"].apply(
        lambda d: d.strftime("%m/%Y") if pd.notnull(d) else ""
    )
else:
    df["DATA_BASE"] = df["DIA"].dt.date
    df["DATA_BASE_LABEL"] = df["DIA"].dt.strftime("%m/%Y")

# Normaliza STATUS_BASE / DESISTIU
df["STATUS_BASE"] = df["STATUS_BASE"].fillna("").astype(str).str.upper()
df.loc[df["STATUS_BASE"].str.contains("DESIST", na=False), "STATUS_BASE"] = "DESISTIU"

# STATUS FINAL GLOBAL POR CLIENTE (regra do DESISTIU)
df_ordenado_global = df.sort_values("DIA")
status_final_por_cliente = (
    df_ordenado_global.groupby("CHAVE_CLIENTE")["STATUS_BASE"].last().fillna("")
)
status_final_por_cliente = status_final_por_cliente.astype(str).str.upper()
status_final_por_cliente.name = "STATUS_FINAL_CLIENTE"

# ---------------------------------------------------------
# SIDEBAR – FILTROS GERAIS
# ---------------------------------------------------------
st.sidebar.header("Filtros")

# Filtro por DATA BASE (mês comercial)
bases_validas = (
    df[["DATA_BASE", "DATA_BASE_LABEL"]]
    .dropna(subset=["DATA_BASE"])
    .drop_duplicates()
    .sort_values("DATA_BASE")
)
opcoes_bases = bases_validas["DATA_BASE_LABEL"].tolist()

if not opcoes_bases:
    st.sidebar.error("Nenhuma DATA BASE encontrada na planilha.")
    st.stop()

default_bases = opcoes_bases[-2:] if len(opcoes_bases) >= 2 else opcoes_bases

bases_selecionadas = st.sidebar.multiselect(
    "Período por DATA BASE (mês comercial)",
    options=opcoes_bases,
    default=default_bases,
)

if not bases_selecionadas:
    bases_selecionadas = opcoes_bases

mask_db = df["DATA_BASE_LABEL"].isin(bases_selecionadas)
df_periodo = df[mask_db].copy()

if df_periodo.empty:
    st.info("Não há movimentações para as DATA BASE selecionadas.")
    st.stop()

# Depois de filtrar por DATA BASE, definimos intervalo real de dias (movimentação)
dias_validos = df_periodo["DIA"].dropna()
if dias_validos.empty:
    hoje = date.today()
    data_ini_mov = hoje - timedelta(days=30)
    data_fim_mov = hoje
else:
    data_ini_mov = dias_validos.min().date()
    data_fim_mov = dias_validos.max().date()

# Tipo de venda considerada
opcao_tipo_venda = st.sidebar.radio(
    "Tipo de venda considerada",
    ("VENDA GERADA + INFORMADA", "Só VENDA GERADA", "Só VENDA INFORMADA"),
    index=0,
)

if opcao_tipo_venda == "Só VENDA GERADA":
    status_vendas_considerados = ["VENDA GERADA"]
    desc_tipo_venda = "Só VENDA GERADA"
elif opcao_tipo_venda == "Só VENDA INFORMADA":
    # Vamos buscar as vendas únicas (GER + INF) e depois filtrar só INF
    status_vendas_considerados = ["VENDA GERADA", "VENDA INFORMADA"]
    desc_tipo_venda = "Só VENDA INFORMADA (último status de venda)"
else:
    status_vendas_considerados = ["VENDA GERADA", "VENDA INFORMADA"]
    desc_tipo_venda = "VENDA GERADA + INFORMADA (último status de venda)"

# Filtro por equipe / corretor
lista_equipe = (
    df_periodo["EQUIPE"].dropna().astype(str).sort_values().unique().tolist()
    if "EQUIPE" in df_periodo.columns
    else []
)
lista_corretor = (
    df_periodo["CORRETOR"].dropna().astype(str).sort_values().unique().tolist()
    if "CORRETOR" in df_periodo.columns
    else []
)

equipe_sel = st.sidebar.selectbox(
    "Equipe",
    options=["Todas"] + lista_equipe,
    index=0,
)

corretor_sel = st.sidebar.selectbox(
    "Corretor",
    options=["Todos"] + lista_corretor,
)

# Meta de vendas (qtde) – slider (iniciando em 30)
meta_vendas = st.sidebar.slider(
    "Meta de vendas (qtde) para o período",
    min_value=0,
    max_value=100,
    value=30,
    step=1,
)

# Aplica filtros de equipe/corretor
if equipe_sel != "Todas":
    df_periodo = df_periodo[df_periodo["EQUIPE"] == equipe_sel]
if corretor_sel != "Todos":
    df_periodo = df_periodo[df_periodo["CORRETOR"] == corretor_sel]

registros_filtrados = len(df_periodo)

if registros_filtrados == 0:
    st.info("Não há movimentações para os filtros selecionados.")
    st.stop()

# Recalcula intervalo de dias após filtros de equipe/corretor
dias_validos_pos = df_periodo["DIA"].dropna()
if not dias_validos_pos.empty:
    data_ini_mov = dias_validos_pos.min().date()
    data_fim_mov = dias_validos_pos.max().date()

# Texto da DATA BASE
if len(bases_selecionadas) == 1:
    txt_base = bases_selecionadas[0]
else:
    txt_base = f"{bases_selecionadas[0]} até {bases_selecionadas[-1]}"

st.caption(
    f"DATA BASE: **{txt_base}** • "
    f"Período (movimentação): **{data_ini_mov.strftime('%d/%m/%Y')}** até "
    f"**{data_fim_mov.strftime('%d/%m/%Y')}** • Registros na base: **{registros_filtrados}**"
    + (f" • Equipe: **{equipe_sel}**" if equipe_sel != "Todas" else "")
    + (f" • Corretor: **{corretor_sel}**" if corretor_sel != "Todos" else "")
    + f" • Tipo de venda considerada: **{desc_tipo_venda}**"
)

# ---------------------------------------------------------
# AGREGAÇÃO PRINCIPAL – VENDAS E KPIs (COM DESISTIU)
# ---------------------------------------------------------

# Sempre pegamos as vendas únicas (GER + INF) aplicando regra DESISTIU global
df_vendas_base = obter_vendas_unicas(
    df_periodo,
    status_vendas=["VENDA GERADA", "VENDA INFORMADA"],
    status_final_map=status_final_por_cliente,
)

if df_vendas_base.empty:
    df_vendas = df_vendas_base.copy()
else:
    status_upper_base = df_vendas_base["STATUS_BASE"].fillna("").astype(str).str.upper()
    if opcao_tipo_venda == "Só VENDA GERADA":
        df_vendas = df_vendas_base[status_upper_base == "VENDA GERADA"].copy()
    elif opcao_tipo_venda == "Só VENDA INFORMADA":
        df_vendas = df_vendas_base[status_upper_base == "VENDA INFORMADA"].copy()
    else:
        df_vendas = df_vendas_base.copy()

qtd_vendas = len(df_vendas)
vgv_total = df_vendas["VGV"].sum() if not df_vendas.empty else 0.0
ticket_medio = vgv_total / qtd_vendas if qtd_vendas > 0 else 0.0

qtd_aprovacoes = conta_aprovacoes(df_periodo["STATUS_BASE"])
taxa_venda_aprov = (qtd_vendas / qtd_aprovacoes * 100) if qtd_aprovacoes > 0 else 0.0

# ---------------------------------------------------------
# LEADS DO CRM NO PERÍODO (session_state["df_leads"])
# ---------------------------------------------------------
df_leads = st.session_state.get("df_leads", pd.DataFrame())
total_leads_periodo = None
leads_por_venda = None

if df_leads is not None and not df_leads.empty:
    col_data_lead = None
    if "data_captura_date" in df_leads.columns:
        col_data_lead = "data_captura_date"
    elif "data_captura" in df_leads.columns:
        df_leads["data_captura"] = pd.to_datetime(
            df_leads["data_captura"], errors="coerce"
        )
        df_leads["data_captura_date"] = df_leads["data_captura"].dt.date
        col_data_lead = "data_captura_date"

    if col_data_lead:
        mask_leads = (df_leads[col_data_lead] >= data_ini_mov) & (
            df_leads[col_data_lead] <= data_fim_mov
        )
        df_leads_periodo = df_leads[mask_leads].copy()
        total_leads_periodo = len(df_leads_periodo)
        if qtd_vendas > 0:
            leads_por_venda = total_leads_periodo / qtd_vendas

perc_meta = (qtd_vendas / meta_vendas * 100) if meta_vendas > 0 else 0.0

# ---------------------------------------------------------
# CÁLCULOS DE VENDAS E EQUIPE PRODUTIVA
# ---------------------------------------------------------
if df_vendas.empty:
    vendas_geradas = 0
    vendas_informadas = 0
else:
    status_vendas_df = df_vendas["STATUS_BASE"].fillna("").astype(str).str.upper()
    vendas_geradas = (status_vendas_df == "VENDA GERADA").sum()
    vendas_informadas = (status_vendas_df == "VENDA INFORMADA").sum()
vendas_totais = vendas_geradas + vendas_informadas

if "CORRETOR" in df_periodo.columns:
    corretores_ativos = df_periodo["CORRETOR"].nunique()
    if df_vendas.empty:
        corretores_com_venda = 0
    else:
        corretores_com_venda = df_vendas["CORRETOR"].nunique()
else:
    corretores_ativos = 0
    corretores_com_venda = 0

perc_equipe_produtiva = (
    corretores_com_venda / corretores_ativos * 100 if corretores_ativos > 0 else 0.0
)

# ---------------------------------------------------------
# CARDS PRINCIPAIS
# ---------------------------------------------------------
st.markdown("## 🏅 Placar de Vendas do Período")

c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1:
    st.metric("Vendas no período", qtd_vendas)
with c2:
    st.metric("VGV Total", format_currency(vgv_total))
with c3:
    st.metric(
        "Ticket médio",
        format_currency(ticket_medio) if ticket_medio > 0 else "R$ 0,00",
    )
with c4:
    st.metric("Meta de vendas (qtde)", meta_vendas)
with c5:
    st.metric("Meta atingida (%)", f"{perc_meta:.1f}%")
with c6:
    st.metric("Taxa Vendas/Aprovações", f"{taxa_venda_aprov:.1f}%")

c7, c8 = st.columns(2)
with c7:
    st.metric(
        "Leads (CRM) no período",
        "-" if total_leads_periodo is None else total_leads_periodo,
    )
with c8:
    st.metric(
        "Leads por venda (CRM)",
        "-" if leads_por_venda is None else f"{leads_por_venda:.1f}",
    )

c9, c10, c11 = st.columns(3)
with c9:
    st.metric("Vendas geradas", vendas_geradas)
with c10:
    st.metric("Vendas informadas", vendas_informadas)
with c11:
    st.metric("Vendas totais (GER + INF)", vendas_totais)

c12, c13, c14 = st.columns(3)
with c12:
    st.metric("Corretores ativos no período", corretores_ativos)
with c13:
    st.metric("Corretores com venda", corretores_com_venda)
with c14:
    st.metric("Equipe produtiva (%)", f"{perc_equipe_produtiva:.1f}%")

# ---------------------------------------------------------
st.markdown("---")
st.markdown("## 📈 Evolução diária das vendas")

if df_vendas.empty:
    st.info("Ainda não há vendas no período selecionado.")
else:
    dr = pd.date_range(start=data_ini_mov, end=data_fim_mov, freq="D")
    dias_periodo = [d.date() for d in dr]

    if len(dias_periodo) == 0:
        st.info("Não há datas válidas no período filtrado para montar os gráficos.")
    else:
        df_diario = (
            df_vendas.groupby(df_vendas["DIA"].dt.date)["VGV"]
            .sum()
            .reindex(dias_periodo, fill_value=0.0)
            .reset_index()
        )
        df_diario.columns = ["DIA", "VGV"]

        df_diario["META_VGV"] = (
            meta_vendas * ticket_medio if ticket_medio > 0 else 0.0
        )

        base = alt.Chart(df_diario).encode(
            x=alt.X("DIA:T", title="Dia"),
        )

        barra_vgv = base.mark_bar().encode(
            y=alt.Y("VGV:Q", title="VGV do dia"),
            tooltip=[
                alt.Tooltip("DIA:T", title="Dia"),
                alt.Tooltip("VGV:Q", title="VGV do dia", format=",.2f"),
            ],
        )

        linha_meta = base.mark_line().encode(
            y=alt.Y("META_VGV:Q", title="Meta VGV (proporcional)"),
        )

        st.altair_chart(barra_vgv + linha_meta, use_container_width=True)

# ---------------------------------------------------------
st.markdown("---")
st.markdown("## 🥇 Ranking de Vendas por Equipe e Corretor")

if df_vendas.empty:
    st.info("Ainda não há vendas para montar o ranking.")
else:
    df_rank_eq = (
        df_vendas.groupby("EQUIPE")
        .agg(QTDE=("STATUS_BASE", "count"), VGV=("VGV", "sum"))
        .reset_index()
    )
    df_rank_eq = df_rank_eq.sort_values("VGV", ascending=False)

    df_rank_cor = (
        df_vendas.groupby(["EQUIPE", "CORRETOR"])
        .agg(QTDE=("STATUS_BASE", "count"), VGV=("VGV", "sum"))
        .reset_index()
    )
    df_rank_cor = df_rank_cor.sort_values("VGV", ascending=False)

    col_r1, col_r2 = st.columns(2)

    with col_r1:
        st.markdown("### 👥 Ranking por Equipe")
        st.dataframe(
            df_rank_eq.style.format({"VGV": "R$ {:,.2f}".format}),
            use_container_width=True,
            hide_index=True,
        )

    with col_r2:
        st.markdown("### 🧑‍💼 Ranking por Corretor")
        st.dataframe(
            df_rank_cor.style.format({"VGV": "R$ {:,.2f}".format}),
            use_container_width=True,
            hide_index=True,
        )

# ---------------------------------------------------------
st.markdown("---")
st.markdown("## 🧱 Mix de Vendas por Construtora e Empreendimento")

if df_vendas.empty:
    st.info("Ainda não há vendas para montar o mix.")
else:
    # 🔹 AGORA COM QTDE DE VENDAS + VGV POR CONSTRUTORA
    df_mix_constr = (
        df_vendas.groupby("CONSTRUTORA_BASE")
        .agg(
            QTDE_VENDAS=("VGV", "size"),
            VGV=("VGV", "sum"),
        )
        .reset_index()
    )
    df_mix_constr = df_mix_constr.sort_values("VGV", ascending=False)

    # 🔹 E QTDE DE VENDAS + VGV POR EMPREENDIMENTO
    df_mix_empre = (
        df_vendas.groupby("EMPREENDIMENTO_BASE")
        .agg(
            QTDE_VENDAS=("VGV", "size"),
            VGV=("VGV", "sum"),
        )
        .reset_index()
    )
    df_mix_empre = df_mix_empre.sort_values("VGV", ascending=False)

    col_m1, col_m2 = st.columns(2)

    with col_m1:
        st.markdown("### 🏗️ Por Construtora")
        st.dataframe(
            df_mix_constr.style.format({"VGV": "R$ {:,.2f}".format}),
            use_container_width=True,
            hide_index=True,
        )

    with col_m2:
        st.markdown("### 🏢 Por Empreendimento")
        st.dataframe(
            df_mix_empre.style.format({"VGV": "R$ {:,.2f}".format}),
            use_container_width=True,
            hide_index=True,
        )

# ---------------------------------------------------------
st.markdown("---")
st.markdown("## 📋 Base de vendas detalhada")

df_tab = df_vendas.copy()

if df_tab.empty:
    st.info("Não há vendas para exibir.")
else:
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
    col_existentes = [c for c in colunas_preferidas if c in df_tab.columns]
    df_tab = df_tab[col_existentes].copy()

    df_tab["Data"] = pd.to_datetime(df_tab["DIA"], errors="coerce").dt.strftime("%d/%m/%Y")
    df_tab = df_tab.drop(columns=["DIA"], errors="ignore")

    df_tab = df_tab.rename(
        columns={
            "NOME_CLIENTE_BASE": "Cliente",
            "CPF_CLIENTE_BASE": "CPF",
            "EQUIPE": "Equipe",
            "CORRETOR": "Corretor",
            "CONSTRUTORA_BASE": "Construtora",
            "EMPREENDIMENTO_BASE": "Empreendimento",
            "STATUS_BASE": "Status",
            "VGV": "VGV",
        }
    )

    # 🔧 CORRIGIDO: pandas usa 'ascending', não 'descending'
    if "Data" in df_tab.columns:
        df_tab = df_tab.sort_values("Data", ascending=False)

    st.dataframe(
        df_tab.style.format({"VGV": "R$ {:,.2f}".format}),
        use_container_width=True,
        hide_index=True,
    )
