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
# CONFIG: LINK DA PLANILHA
# ---------------------------------------------------------
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID_ANALISES = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ANALISES}"


def limpar_para_data(serie):
    dt = pd.to_datetime(serie, dayfirst=True, errors="coerce")
    return dt.dt.date


@st.cache_data(ttl=60)
def carregar_dados():
    df = pd.read_csv(CSV_URL)
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

    df["CONSTRUTORA_BASE"] = (
        df[col_construtora].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
        if col_construtora
        else "NÃO INFORMADO"
    )

    df["EMPREENDIMENTO_BASE"] = (
        df[col_empreend].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
        if col_empreend
        else "NÃO INFORMADO"
    )

    # SITUAÇÃO BASE
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
        status = df[col_situacao].fillna("").astype(str).str.upper()
        df.loc[status.str.contains("EM ANÁLISE"), "STATUS_BASE"] = "EM ANÁLISE"
        df.loc[status.str.contains("REANÁLISE"), "STATUS_BASE"] = "REANÁLISE"
        df.loc[status.str.contains("APROV"), "STATUS_BASE"] = "APROVADO"
        df.loc[status.str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
        df.loc[status.str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA GERADA"
        df.loc[status.str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA INFORMADA"

    # VGV
    if "OBSERVAÇÕES" in df.columns:
        df["VGV"] = pd.to_numeric(df["OBSERVAÇÕES"], errors="coerce").fillna(0.0)
    else:
        df["VGV"] = 0.0

    # NOME / CPF
    possiveis_nome = ["NOME", "CLIENTE", "NOME CLIENTE", "NOME DO CLIENTE"]
    possiveis_cpf = ["CPF", "CPF CLIENTE", "CPF DO CLIENTE"]

    col_nome = next((c for c in possiveis_nome if c in df.columns), None)
    col_cpf = next((c for c in possiveis_cpf if c in df.columns), None)

    df["NOME_CLIENTE_BASE"] = (
        df[col_nome].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
        if col_nome
        else "NÃO INFORMADO"
    )
    df["CPF_CLIENTE_BASE"] = (
        df[col_cpf].fillna("").astype(str).str.replace(r"\D", "", regex=True)
        if col_cpf
        else ""
    )

    return df


df = carregar_dados()
if df.empty:
    st.error("Não foi possível carregar dados da planilha.")
    st.stop()

# LEADS DO SUPREMO (se existir no session_state)
df_leads = st.session_state.get("df_leads", pd.DataFrame())


def conta_aprovacoes(s):
    return (s == "APROVADO").sum()


def obter_vendas_unicas(df_scope: pd.DataFrame) -> pd.DataFrame:
    df_v = df_scope[df_scope["STATUS_BASE"].isin(["VENDA GERADA", "VENDA INFORMADA"])].copy()
    if df_v.empty:
        return df_v

    df_v["CHAVE_CLIENTE"] = (
        df_v["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO")
        + " | "
        + df_v["CPF_CLIENTE_BASE"].fillna("")
    )
    df_v = df_v.sort_values("DIA")
    df_v_ult = df_v.groupby("CHAVE_CLIENTE").tail(1)
    return df_v_ult


# ---------------------------------------------------------
# SIDEBAR – FILTROS
# ---------------------------------------------------------
st.sidebar.title("Filtros 🔎")

hoje = date.today()
dias_validos = pd.Series(df["DIA"].dropna())

if not dias_validos.empty:
    data_min = dias_validos.min()
    data_max_base = dias_validos.max()
else:
    data_max_base = hoje
    data_min = hoje - timedelta(days=30)

data_ini_default = max(data_min, data_max_base - timedelta(days=30))
data_fim_default = max(data_max_base, hoje)
max_picker = hoje + timedelta(days=365)

periodo = st.sidebar.date_input(
    "Período das vendas",
    value=(data_ini_default, data_fim_default),
    min_value=data_min,
    max_value=max_picker,
)

if isinstance(periodo, tuple) and len(periodo) == 2:
    data_ini_sel, data_fim_sel = periodo
else:
    data_ini_sel, data_fim_sel = data_ini_default, data_fim_default

if data_ini_sel > data_fim_sel:
    st.sidebar.error("Data inicial não pode ser maior que a data final.")
    st.stop()

# data real considerada pros dados (não passa de hoje)
data_fim_real = min(data_fim_sel, hoje)

# Filtro de equipe / corretor
lista_equipes = sorted(df["EQUIPE"].dropna().unique())
equipe_sel = st.sidebar.selectbox("Equipe", ["Todas"] + lista_equipes)

base_corretor = df if equipe_sel == "Todas" else df[df["EQUIPE"] == equipe_sel]
lista_corretor = sorted(base_corretor["CORRETOR"].dropna().unique())
corretor_sel = st.sidebar.selectbox("Corretor", ["Todos"] + lista_corretor)

# Meta de vendas
meta_vendas = st.sidebar.slider(
    "Meta de vendas (qtde) para o período",
    min_value=0,
    max_value=100,
    value=10,
    step=1,
)

# ---------------------------------------------------------
# APLICA FILTROS NOS DADOS (USANDO data_fim_real)
# ---------------------------------------------------------
df_periodo = df.copy()
dia_series_all = limpar_para_data(df_periodo["DIA"])
mask_data = (dia_series_all >= data_ini_sel) & (dia_series_all <= data_fim_real)
df_periodo = df_periodo[mask_data]

if equipe_sel != "Todas":
    df_periodo = df_periodo[df_periodo["EQUIPE"] == equipe_sel]
if corretor_sel != "Todos":
    df_periodo = df_periodo[df_periodo["CORRETOR"] == corretor_sel]

registros_filtrados = len(df_periodo)

texto_periodo = (
    f"Período selecionado: **{data_ini_sel.strftime('%d/%m/%Y')}** "
    f"até **{data_fim_sel.strftime('%d/%m/%Y')}**"
)
if data_fim_real < data_fim_sel:
    texto_periodo += f" • Dados considerados até **{data_fim_real.strftime('%d/%m/%Y')}**"

texto_periodo += f" • Registros na base: **{registros_filtrados}**"
if equipe_sel != "Todas":
    texto_periodo += f" • Equipe: **{equipe_sel}**"
if corretor_sel != "Todos":
    texto_periodo += f" • Corretor: **{corretor_sel}**"

st.caption(texto_periodo)

if df_periodo.empty:
    st.warning("Não há registros para os filtros selecionados.")
    st.stop()

# ---------------------------------------------------------
# VENDAS ÚNICAS / KPIs
# ---------------------------------------------------------
df_vendas = obter_vendas_unicas(df_periodo)
qtd_vendas = len(df_vendas)
vgv_total = df_vendas["VGV"].sum()
ticket_medio = vgv_total / qtd_vendas if qtd_vendas > 0 else 0

qtd_aprovacoes = conta_aprovacoes(df_periodo["STATUS_BASE"])
taxa_venda_aprov = (qtd_vendas / qtd_aprovacoes * 100) if qtd_aprovacoes > 0 else 0

# Leads do CRM também limitados até data_fim_real
df_leads = st.session_state.get("df_leads", pd.DataFrame())
total_leads_periodo = None
if not df_leads.empty and "data_captura" in df_leads.columns:
    df_leads_use = df_leads.dropna(subset=["data_captura"]).copy()
    df_leads_use["data_captura"] = pd.to_datetime(df_leads_use["data_captura"], errors="coerce")
    df_leads_use["data_captura_date"] = df_leads_use["data_captura"].dt.date

    mask_leads_periodo = (
        (df_leads_use["data_captura_date"] >= data_ini_sel)
        & (df_leads_use["data_captura_date"] <= data_fim_real)
    )
    df_leads_periodo = df_leads_use[mask_leads_periodo].copy()
    total_leads_periodo = len(df_leads_periodo)

leads_por_venda = (
    total_leads_periodo / qtd_vendas if total_leads_periodo is not None and qtd_vendas > 0 else None
)

perc_meta = (qtd_vendas / meta_vendas * 100) if meta_vendas > 0 else 0

# ---------------------------------------------------------
# KPIs
# ---------------------------------------------------------
st.markdown("## 🏅 Placar de Vendas do Período")

c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1:
    st.metric("Vendas no período", qtd_vendas)
with c2:
    st.metric("VGV Total", f"R$ {vgv_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
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
    st.metric("Leads (CRM) no período", "-" if total_leads_periodo is None else total_leads_periodo)
with c8:
    st.metric("Leads por venda (CRM)", "-" if leads_por_venda is None else f"{leads_por_venda:.1f}")

# ---------------------------------------------------------
# EVOLUÇÃO DIÁRIA
# ---------------------------------------------------------
st.markdown("---")
st.markdown("## 📈 Evolução diária das vendas")

if df_vendas.empty:
    st.info("Ainda não há vendas no período selecionado.")
else:
    # base real de vendas por dia (até data_fim_real)
    df_vendas_dia_real = (
        df_vendas.groupby("DIA")
        .agg(
            VGV_DIA=("VGV", "sum"),
            QTD_VENDAS=("STATUS_BASE", "count"),
        )
        .reset_index()
    )

    # calendário completo do período selecionado (data_ini_sel -> data_fim_sel)
    datas_range = pd.date_range(start=data_ini_sel, end=data_fim_sel, freq="D")
    df_dias = pd.DataFrame({"DIA": datas_range.date})

    # junta vendas nesse calendário
    df_vendas_dia = df_dias.merge(df_vendas_dia_real, on="DIA", how="left")
    df_vendas_dia["VGV_DIA"] = df_vendas_dia["VGV_DIA"].fillna(0.0)
    df_vendas_dia["QTD_VENDAS"] = df_vendas_dia["QTD_VENDAS"].fillna(0).astype(int)
    df_vendas_dia = df_vendas_dia.sort_values("DIA")

    df_vendas_dia["DIA_STR"] = pd.to_datetime(df_vendas_dia["DIA"]).dt.strftime("%d/%m")

    # VGV por dia (barras) – vai mostrar só onde houve venda > 0
    st.markdown("### 💵 VGV por dia")
    chart_vgv_dia = (
        alt.Chart(df_vendas_dia[df_vendas_dia["VGV_DIA"] > 0])
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

    # VGV acumulado + meta acumulada
    st.markdown("### 📊 VGV acumulado no período")
    df_vendas_dia["VGV_ACUM"] = df_vendas_dia["VGV_DIA"].cumsum()

    n_dias_periodo = len(df_vendas_dia)
    if meta_vendas > 0 and ticket_medio > 0 and n_dias_periodo > 0:
        meta_total_vgv = meta_vendas * ticket_medio
        meta_diaria_vgv = meta_total_vgv / n_dias_periodo
        df_vendas_dia["META_VGV_ACUM"] = [
            meta_diaria_vgv * (i + 1) for i in range(n_dias_periodo)
        ]
    else:
        df_vendas_dia["META_VGV_ACUM"] = np.nan

    if df_vendas_dia["META_VGV_ACUM"].notna().any():
        df_plot = df_vendas_dia[["DIA_STR", "VGV_ACUM", "META_VGV_ACUM"]].copy()
        df_plot = df_plot.melt(
            id_vars=["DIA_STR"],
            value_vars=["VGV_ACUM", "META_VGV_ACUM"],
            var_name="Série",
            value_name="VGV_VAL",
        )
        df_plot["Série"] = df_plot["Série"].replace(
            {"VGV_ACUM": "Realizado", "META_VGV_ACUM": "Meta"}
        )

        chart_vgv_acum = (
            alt.Chart(df_plot)
            .mark_line(point=True)
            .encode(
                x=alt.X("DIA_STR:N", title="Dia"),
                y=alt.Y("VGV_VAL:Q", title="VGV acumulado (R$)"),
                color=alt.Color("Série:N", title=""),
                tooltip=[
                    alt.Tooltip("DIA_STR:N", title="Dia"),
                    alt.Tooltip("Série:N", title="Série"),
                    alt.Tooltip("VGV_VAL:Q", title="VGV acumulado", format=",.2f"),
                ],
            )
            .properties(height=300)
        )
    else:
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
        rank_eq["VENDAS"] > 0, rank_eq["VGV"] / rank_eq["VENDAS"], 0
    )
    rank_eq["%_VGV_IMOB"] = rank_eq["VGV"] / vgv_total * 100 if vgv_total > 0 else 0.0
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
        rank_cor["VENDAS"] > 0, rank_cor["VGV"] / rank_cor["VENDAS"], 0
    )
    rank_cor["%_VGV_IMOB"] = rank_cor["VGV"] / vgv_total * 100 if vgv_total > 0 else 0.0
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
# MIX DE VENDAS
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
            .agg(QTDE_VENDAS=("VGV", "size"), VGV=("VGV", "sum"))
            .reset_index()
            .sort_values("VGV", ascending=False)
        )
        st.dataframe(
            mix_const.style.format({"VGV": "R$ {:,.2f}".format}),
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
# TABELA DETALHADA
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

if "DIA" in df_tab.columns:
    df_tab["DIA"] = pd.to_datetime(df_tab["DIA"], errors="coerce").dt.strftime("%d/%m/%Y")

df_tab = df_tab.rename(
    columns={
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
)

if "Data" in df_tab.columns:
    df_tab = df_tab.sort_values("Data", ascending=False)

st.dataframe(
    df_tab.style.format({"VGV": "R$ {:,.2f}".format}),
    use_container_width=True,
    hide_index=True,
)
