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
# LINK DA PLANILHA
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

    # Padroniza colunas
    df.columns = [c.strip().upper() for c in df.columns]

    # DATA / DIA (primeiro como date)
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

    # VGV (OBSERVAÇÕES)
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

# Agora DIA vira datetime (igual Funil Imobiliária)
df["DIA"] = pd.to_datetime(df["DIA"], errors="coerce")

# Leads do Supremo se tiver no session_state
df_leads = st.session_state.get("df_leads", pd.DataFrame())


def conta_aprovacoes(s):
    return (s.fillna("").astype(str).str.upper() == "APROVADO").sum()


def obter_vendas_unicas(df_scope: pd.DataFrame) -> pd.DataFrame:
    """Uma venda por cliente (último status VENDA GERADA / INFORMADA)."""
    if df_scope.empty:
        return df_scope.copy()

    s = df_scope["STATUS_BASE"].fillna("").astype(str).str.upper()
    df_v = df_scope[s.isin(["VENDA GERADA", "VENDA INFORMADA"])].copy()
    if df_v.empty:
        return df_v

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
# DEFINIÇÃO DO PERÍODO (MESMA LÓGICA DO FUNIL)
# ---------------------------------------------------------
hoje = date.today()
dias_validos = df["DIA"].dropna()

if dias_validos.empty:
    data_min_mov = hoje - timedelta(days=30)
    data_max_mov = hoje
else:
    data_min_mov = dias_validos.min().date()
    data_max_mov = dias_validos.max().date()

# pode escolher data futura até +365 dias
max_futuro = max(data_max_mov, hoje) + timedelta(days=365)

st.sidebar.title("Filtros 🔎")

data_ini_default_mov = max(data_min_mov, data_max_mov - timedelta(days=30))
periodo_mov = st.sidebar.date_input(
    "Período das vendas (data de movimentação)",
    value=(data_ini_default_mov, data_max_mov),
    min_value=data_min_mov,
    max_value=max_futuro,
)

if isinstance(periodo_mov, tuple) and len(periodo_mov) == 2:
    data_ini_mov, data_fim_mov = periodo_mov
else:
    data_ini_mov = periodo_mov
    data_fim_mov = periodo_mov

if data_ini_mov > data_fim_mov:
    data_ini_mov, data_fim_mov = data_fim_mov, data_ini_mov

# Filtro de equipe / corretor
lista_equipes = sorted(df["EQUIPE"].dropna().unique())
equipe_sel = st.sidebar.selectbox("Equipe", ["Todas"] + lista_equipes)

base_corretor = df if equipe_sel == "Todas" else df[df["EQUIPE"] == equipe_sel]
lista_corretor = sorted(base_corretor["CORRETOR"].dropna().unique())
corretor_sel = st.sidebar.selectbox("Corretor", ["Todos"] + lista_corretor)

# Meta de vendas (qtde) – slider
meta_vendas = st.sidebar.slider(
    "Meta de vendas (qtde) para o período",
    min_value=0,
    max_value=100,
    value=10,
    step=1,
)

# ---------------------------------------------------------
# APLICA FILTROS NO DATAFRAME
# ---------------------------------------------------------
mask_mov = (df["DIA"].dt.date >= data_ini_mov) & (df["DIA"].dt.date <= data_fim_mov)
df_periodo = df[mask_mov].copy()

if equipe_sel != "Todas":
    df_periodo = df_periodo[df_periodo["EQUIPE"] == equipe_sel]
if corretor_sel != "Todos":
    df_periodo = df_periodo[df_periodo["CORRETOR"] == corretor_sel]

registros_filtrados = len(df_periodo)

st.caption(
    f"Período (movimentação): **{data_ini_mov.strftime('%d/%m/%Y')}** até "
    f"**{data_fim_mov.strftime('%d/%m/%Y')}** • Registros na base: **{registros_filtrados}**"
    + (f" • Equipe: **{equipe_sel}**" if equipe_sel != "Todas" else "")
    + (f" • Corretor: **{corretor_sel}**" if corretor_sel != "Todos" else "")
)

if df_periodo.empty:
    st.warning("Nenhum registro encontrado para o período selecionado.")
    st.stop()

# ---------------------------------------------------------
# VENDAS ÚNICAS E KPIs
# ---------------------------------------------------------
df_vendas = obter_vendas_unicas(df_periodo)
qtd_vendas = len(df_vendas)
vgv_total = df_vendas["VGV"].sum() if not df_vendas.empty else 0.0
ticket_medio = vgv_total / qtd_vendas if qtd_vendas > 0 else 0.0

qtd_aprovacoes = conta_aprovacoes(df_periodo["STATUS_BASE"])
taxa_venda_aprov = (qtd_vendas / qtd_aprovacoes * 100) if qtd_aprovacoes > 0 else 0.0

# ---------------------------------------------------------
# LEADS DO CRM NO PERÍODO (AGORA FILTRANDO POR EQUIPE/CORRETOR)
# ---------------------------------------------------------
total_leads_periodo = None
leads_por_venda = None

if not df_leads.empty:

    df_leads_use = df_leads.copy()

    # Garante coluna de data
    if "data_captura_date" in df_leads_use.columns:
        base_date_col = "data_captura_date"
    elif "data_captura" in df_leads_use.columns:
        df_leads_use["data_captura"] = pd.to_datetime(
            df_leads_use["data_captura"], errors="coerce"
        )
        df_leads_use["data_captura_date"] = df_leads_use["data_captura"].dt.date
        base_date_col = "data_captura_date"
    else:
        base_date_col = None

    if base_date_col is not None:
        df_leads_use = df_leads_use.dropna(subset=[base_date_col]).copy()

        # Filtro por período
        mask_leads_periodo = (
            (df_leads_use[base_date_col] >= data_ini_mov)
            & (df_leads_use[base_date_col] <= data_fim_mov)
        )
        df_leads_periodo = df_leads_use[mask_leads_periodo].copy()

        # Filtro por equipe (se existir essa coluna)
        if equipe_sel != "Todas" and "equipe_lead_norm" in df_leads_periodo.columns:
            df_leads_periodo = df_leads_periodo[
                df_leads_periodo["equipe_lead_norm"] == equipe_sel
            ]

        # Filtro por corretor (se existir essa coluna)
        if corretor_sel != "Todos" and "nome_corretor_norm" in df_leads_periodo.columns:
            df_leads_periodo = df_leads_periodo[
                df_leads_periodo["nome_corretor_norm"] == corretor_sel
            ]

        total_leads_periodo = len(df_leads_periodo)

        if total_leads_periodo > 0 and qtd_vendas > 0:
            leads_por_venda = total_leads_periodo / qtd_vendas

perc_meta = (qtd_vendas / meta_vendas * 100) if meta_vendas > 0 else 0.0

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
    st.metric("Ticket médio", format_currency(ticket_medio) if ticket_medio > 0 else "R$ 0,00")
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
# EVOLUÇÃO DIÁRIA – VGV E LINHA DE META
# ---------------------------------------------------------
st.markdown("---")
st.markdown("## 📈 Evolução diária das vendas")

if df_vendas.empty:
    st.info("Ainda não há vendas no período selecionado.")
else:
    # calendário completo do período selecionado
    dr = pd.date_range(start=data_ini_mov, end=data_fim_mov, freq="D")
    dias_periodo = [d.date() for d in dr]

    if len(dias_periodo) == 0:
        st.info("Não há datas válidas no período filtrado para montar os gráficos.")
    else:
        idx = pd.to_datetime(dias_periodo)
        df_line = pd.DataFrame(index=idx)
        df_line.index.name = "DIA"

        # VGV por dia (somando vendas únicas)
        df_temp = df_vendas.copy()
        df_temp["DIA_DATA"] = pd.to_datetime(df_temp["DIA"]).dt.date
        vgv_por_dia = (
            df_temp.groupby("DIA_DATA")["VGV"]
            .sum()
            .reindex(dias_periodo, fill_value=0.0)
        )

        df_line["VGV_DIA"] = vgv_por_dia.values
        df_line["VGV_ACUM"] = df_line["VGV_DIA"].cumsum()

        # gráfico de barras VGV por dia (apenas dias com VGV > 0)
        df_barras = df_line.reset_index().copy()
        df_barras["DIA_STR"] = df_barras["DIA"].dt.strftime("%d/%m")

        st.markdown("### 💵 VGV por dia")
        chart_vgv_dia = (
            alt.Chart(df_barras[df_barras["VGV_DIA"] > 0])
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("DIA_STR:N", title="Dia"),
                y=alt.Y("VGV_DIA:Q", title="VGV do dia (R$)"),
                tooltip=[
                    alt.Tooltip("DIA_STR:N", title="Dia"),
                    alt.Tooltip("VGV_DIA:Q", title="VGV do dia", format=",.2f"),
                ],
            )
            .properties(height=300)
        )
        st.altair_chart(chart_vgv_dia, use_container_width=True)

        # --------- VGV acumulado x Meta ---------
        st.markdown("### 📊 VGV acumulado no período")

        hoje_date = date.today()
        limite_real = min(hoje_date, data_fim_mov)
        mask_future = df_line.index.date > limite_real
        df_line_real = df_line.copy()
        df_line_real.loc[mask_future, "VGV_ACUM"] = np.nan

        if meta_vendas > 0 and ticket_medio > 0:
            meta_total_vgv = meta_vendas * ticket_medio
            df_line_real["META_ACUM"] = np.linspace(
                0, meta_total_vgv, num=len(df_line_real), endpoint=True
            )
        else:
            df_line_real["META_ACUM"] = np.nan

        df_plot = df_line_real.reset_index().copy()
        df_plot["DIA_STR"] = df_plot["DIA"].dt.strftime("%d/%m")

        if df_plot["META_ACUM"].notna().any():
            df_melt = df_plot.melt(
                id_vars=["DIA", "DIA_STR"],
                value_vars=["VGV_ACUM", "META_ACUM"],
                var_name="Série",
                value_name="VGV_VAL",
            )
            df_melt["Série"] = df_melt["Série"].replace(
                {"VGV_ACUM": "Realizado", "META_ACUM": "Meta"}
            )
        else:
            df_melt = df_plot[["DIA", "DIA_STR", "VGV_ACUM"]].copy()
            df_melt = df_melt.rename(columns={"VGV_ACUM": "VGV_VAL"})
            df_melt["Série"] = "Realizado"

        chart_acum = (
            alt.Chart(df_melt)
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
            .properties(height=320)
        )

        # ponto do dia de hoje, se estiver no período
        hoje_dentro = (hoje_date >= data_ini_mov) and (hoje_date <= data_fim_mov)
        if hoje_dentro:
            df_real_reset = df_line_real.reset_index()
            df_real_hoje = df_real_reset[df_real_reset["DIA"].dt.date == limite_real]
            if not df_real_hoje.empty:
                ponto_hoje = (
                    alt.Chart(
                        df_real_hoje.assign(
                            DIA_STR=df_real_hoje["DIA"].dt.strftime("%d/%m")
                        )
                    )
                    .mark_point(size=80)
                    .encode(
                        x="DIA_STR:N",
                        y="VGV_ACUM:Q",
                    )
                )
                chart_acum = chart_acum + ponto_hoje

        st.altair_chart(chart_acum, use_container_width=True)
        st.caption(
            "Linha **Realizado** mostra o VGV acumulado por dia e para no **dia de hoje**. "
            "Linha **Meta** vai até a data final escolhida e mostra o ritmo de VGV necessário "
            "para bater a meta de vendas configurada no período."
        )

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
