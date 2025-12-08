import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Controle de Atendimento de Leads",
    page_icon="📞",
    layout="wide",
)

# Logo MR Imóveis na lateral (se quiser manter)
st.sidebar.image("logo_mr.png", use_column_width=True)

st.title("📞 Controle de Atendimento de Leads")
st.caption(
    "Visão simples e operacional do atendimento: leads atendidos, não atendidos, tempo de atendimento e leads novos."
)

# ---------------------------------------------------------
# OBTENDO O DATAFRAME DE LEADS (VINDO DO app_dashboard)
# ---------------------------------------------------------
if "df_leads" not in st.session_state or st.session_state["df_leads"] is None:
    st.error(
        "Nenhum dado de leads encontrado. Volte para a página principal do dashboard para carregar os dados."
    )
    st.stop()

df_raw = st.session_state["df_leads"].copy()

# ---------------------------------------------------------
# FUNÇÃO PARA MAPEAR COLUNAS PELO NOME APROXIMADO
# ---------------------------------------------------------
def get_col(possiveis_nomes):
    cols_lower = {c.lower(): c for c in df_raw.columns}
    for nome in possiveis_nomes:
        nome_lower = nome.lower()
        for base, real in cols_lower.items():
            if nome_lower in base:
                return real
    return None


# ---------------------------------------------------------
# NORMALIZAÇÃO DAS PRINCIPAIS COLUNAS
# ---------------------------------------------------------

df = df_raw.copy()

# Nome do lead
col_nome_lead = get_col(["nome", "lead", "contato"])
if col_nome_lead:
    df["NOME_LEAD"] = df[col_nome_lead].astype(str)
else:
    df["NOME_LEAD"] = ""

# Telefone / WhatsApp
col_telefone = get_col(["telefone", "celular", "whatsapp"])
if col_telefone:
    df["TELEFONE_LEAD"] = df[col_telefone].astype(str)
else:
    df["TELEFONE_LEAD"] = ""

# Corretor / Responsável
col_corretor = get_col(["corretor", "responsavel", "responsável", "consultor", "usuário", "usuario"])
if col_corretor:
    df["CORRETOR_EXIBICAO"] = df[col_corretor].fillna("SEM CORRETOR").astype(str)
else:
    df["CORRETOR_EXIBICAO"] = "SEM CORRETOR"

# ✅ Coluna amigável para exibição
df["Corretor responsável"] = df["CORRETOR_EXIBICAO"]

# Situação / Status
col_situacao = get_col(["situacao", "situação", "status"])

# Etapa / Fase do funil
col_etapa = get_col(["etapa", "fase", "pipeline", "funil"])

# Datas principais
col_data_captura = get_col(["data_captura", "data de captura", "criado_em", "data_criacao", "data entrada"])
if col_data_captura:
    df["DATA_CAPTURA_DT"] = pd.to_datetime(df[col_data_captura], errors="coerce")
else:
    df["DATA_CAPTURA_DT"] = pd.NaT

col_data_primeiro_contato = get_col(
    ["data_primeiro_contato", "data_1_contato", "data_contato", "data_com_corretor"]
)
if col_data_primeiro_contato:
    df["DATA_COM_CORRETOR_DT"] = pd.to_datetime(
        df[col_data_primeiro_contato], errors="coerce"
    )
else:
    df["DATA_COM_CORRETOR_DT"] = pd.NaT

col_data_ult_interacao = get_col(
    ["data_ultima_interacao", "data_última_interacao", "data_ultima_atividade"]
)
if col_data_ult_interacao:
    df["DATA_ULT_INTERACAO_DT"] = pd.to_datetime(
        df[col_data_ult_interacao], errors="coerce"
    )
else:
    df["DATA_ULT_INTERACAO_DT"] = pd.NaT

# Leads perdidos (por situação/etapa que indique perda, se disponível)
df["PERDIDO"] = False
if col_situacao:
    situ_norm = df[col_situacao].fillna("").astype(str).str.upper()
    df["PERDIDO"] = situ_norm.str.contains("PERDIDO|DESCARTADO|SEM INTERESSE|NÃO TEM INTERESSE")
elif col_etapa:
    etapa_norm = df[col_etapa].fillna("").astype(str).str.upper()
    df["PERDIDO"] = etapa_norm.str.contains("PERDIDO|DESCARTADO|SEM INTERESSE|NÃO TEM INTERESSE")

# Lead atendido (teve primeiro contato)
df["ATENDIDO"] = df["DATA_COM_CORRETOR_DT"].notna()

# Tempo de atendimento (minutos entre captura e 1º contato)
df["TEMPO_ATEND_MIN"] = (
    (df["DATA_COM_CORRETOR_DT"] - df["DATA_CAPTURA_DT"]).dt.total_seconds() / 60.0
)

# Tempo entre interações (1º contato -> última interação)
df["TEMPO_INTERACOES_MIN"] = (
    (df["DATA_ULT_INTERACAO_DT"] - df["DATA_COM_CORRETOR_DT"]).dt.total_seconds()
    / 60.0
)


def format_minutes(val):
    if pd.isna(val):
        return "-"
    try:
        val = int(round(val))
        horas = val // 60
        minutos = val % 60
        if horas > 0:
            return f"{horas}h {minutos:02d}min"
        return f"{minutos} min"
    except Exception:
        return "-"


def fmt_dt(dt):
    if pd.isna(dt):
        return ""
    return dt.strftime("%d/%m/%Y %H:%M")


# ---------------------------------------------------------
# FILTROS LATERAIS
# ---------------------------------------------------------

st.sidebar.header("Filtros – Atendimento de Leads")

data_min = df["DATA_CAPTURA_DT"].min()
data_max = df["DATA_CAPTURA_DT"].max()

if pd.isna(data_min) or pd.isna(data_max):
    st.warning("Não foi possível identificar o intervalo de datas dos leads.")
    data_ini_default = datetime.today() - timedelta(days=7)
    data_fim_default = datetime.today()
else:
    data_min_date = data_min.date()
    data_max_date = data_max.date()
    data_ini_default = max(data_min_date, data_max_date - timedelta(days=7))
    data_fim_default = data_max_date

data_ini = st.sidebar.date_input("Data inicial (captura do lead)", value=data_ini_default)
data_fim = st.sidebar.date_input("Data final (captura do lead)", value=data_fim_default)

if data_ini > data_fim:
    st.sidebar.error("A data inicial não pode ser maior que a data final.")
    st.stop()

mask_periodo = (df["DATA_CAPTURA_DT"].dt.date >= data_ini) & (
    df["DATA_CAPTURA_DT"].dt.date <= data_fim
)
df_periodo = df[mask_periodo].copy()

# Filtro de corretor
corretores = sorted(df_periodo["Corretor responsável"].dropna().unique().tolist())
opcoes_corretor = ["Todos"] + corretores
corretor_sel = st.sidebar.selectbox("Corretor", opcoes_corretor)

if corretor_sel != "Todos":
    df_periodo = df_periodo[df_periodo["Corretor responsável"] == corretor_sel]

if df_periodo.empty:
    st.warning("Nenhum lead encontrado com os filtros selecionados.")
    st.stop()

st.write(
    f"Período selecionado: **{data_ini.strftime('%d/%m/%Y')} até {data_fim.strftime('%d/%m/%Y')}** "
    f"• Leads no período (sem perdidos): **{len(df_periodo[~df_periodo['PERDIDO']])}**"
)

# ---------------------------------------------------------
# KPIs GERAIS
# ---------------------------------------------------------

leads_no_periodo = len(df_periodo)
leads_atendidos = df_periodo["ATENDIDO"].sum()
leads_nao_atendidos = leads_no_periodo - leads_atendidos
leads_perdidos = df_periodo["PERDIDO"].sum()

# Tempo médio de atendimento (apenas atendidos)
tempo_medio_min = df_periodo.loc[df_periodo["ATENDIDO"], "TEMPO_ATEND_MIN"].mean()
tempo_medio_fmt = format_minutes(tempo_medio_min) if not pd.isna(tempo_medio_min) else "-"

# Leads novos = não perdidos e não atendidos
mask_novos = (~df_periodo["PERDIDO"]) & (~df_periodo["ATENDIDO"])
df_leads_novos = df_periodo[mask_novos].copy()
qtd_leads_novos = len(df_leads_novos)

# % atendidos em até 15 minutos
mask_ate15 = (df_periodo["ATENDIDO"]) & (df_periodo["TEMPO_ATEND_MIN"] <= 15)
qtd_ate15 = mask_ate15.sum()
perc_ate15 = (qtd_ate15 / leads_atendidos * 100) if leads_atendidos > 0 else 0

st.markdown("## 🧾 Visão geral do atendimento")

# Inclui card de leads novos
c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
c1.metric("Leads no período", leads_no_periodo)
c2.metric("Leads atendidos", leads_atendidos)
c3.metric("Leads não atendidos", leads_nao_atendidos)
c4.metric("Leads perdidos no período", leads_perdidos)
c5.metric("Tempo médio de atendimento", tempo_medio_fmt)
c6.metric("Leads novos", qtd_leads_novos)
c7.metric("% atendidos em até 15 min", f"{perc_ate15:.1f}%")

st.markdown("### 📥 Leads novos (não perdidos e ainda não atendidos)")
if qtd_leads_novos > 0:
    cols_exibir = [
        "NOME_LEAD",
        "TELEFONE_LEAD",
        "Corretor responsável",
        "DATA_CAPTURA_DT",
    ]
    cols_exibir = [c for c in cols_exibir if c in df_leads_novos.columns]
    df_tmp = df_leads_novos.copy()
    if "DATA_CAPTURA_DT" in df_tmp.columns:
        df_tmp["Data captura"] = df_tmp["DATA_CAPTURA_DT"].apply(fmt_dt)
        cols_exibir = [c for c in cols_exibir if c != "DATA_CAPTURA_DT"] + [
            "Data captura"
        ]
    st.dataframe(df_tmp[cols_exibir], use_container_width=True)
else:
    st.button("↑ Nenhum lead novo", disabled=True)

# ---------------------------------------------------------
# RESUMO GERAL POR CORRETOR
# ---------------------------------------------------------

st.markdown("## 👥 Resumo geral por corretor")

df_cor = df_periodo.copy()

agr = df_cor.groupby("Corretor responsável").agg(
    LEADS_PERIODO=("NOME_LEAD", "count"),
    LEADS_ATENDIDOS=("ATENDIDO", "sum"),
    TEMPO_MEDIO_ATEND_MIN=("TEMPO_ATEND_MIN", "mean"),
    TEMPO_MEDIO_INTERACOES_MIN=("TEMPO_INTERACOES_MIN", "mean"),
).reset_index()

agr["Tempo médio atendimento"] = agr["TEMPO_MEDIO_ATEND_MIN"].apply(format_minutes)
agr["Tempo médio entre interações"] = agr[
    "TEMPO_MEDIO_INTERACOES_MIN"
].apply(format_minutes)

cols_resumo = [
    "Corretor responsável",
    "LEADS_PERIODO",
    "LEADS_ATENDIDOS",
    "Tempo médio atendimento",
    "Tempo médio entre interações",
]

st.dataframe(agr[cols_resumo], use_container_width=True)

# ---------------------------------------------------------
# DETALHAMENTO DOS LEADS
# ---------------------------------------------------------

st.markdown("## 📂 Detalhamento dos leads")

aba1, aba2, aba3 = st.tabs(["Atendidos", "Não atendidos", "Apenas 1 contato"])

with aba1:
    df_atendidos = df_periodo[df_periodo["ATENDIDO"] & (~df_periodo["PERDIDO"])].copy()
    if df_atendidos.empty:
        st.info("Nenhum lead atendido no período.")
    else:
        df_atendidos["Captura"] = df_atendidos["DATA_CAPTURA_DT"].apply(fmt_dt)
        df_atendidos["1º contato"] = df_atendidos["DATA_COM_CORRETOR_DT"].apply(fmt_dt)
        df_atendidos["Última interação"] = df_atendidos[
            "DATA_ULT_INTERACAO_DT"
        ].apply(fmt_dt)
        df_atendidos["Tempo atendimento"] = df_atendidos["TEMPO_ATEND_MIN"].apply(
            format_minutes
        )

        cols = [
            "NOME_LEAD",
            "TELEFONE_LEAD",
            "Corretor responsável",
            "Captura",
            "1º contato",
            "Última interação",
            "Tempo atendimento",
            col_situacao,
            col_etapa,
        ]
        cols = [c for c in cols if c in df_atendidos.columns]
        st.dataframe(df_atendidos[cols], use_container_width=True)

with aba2:
    df_nao = df_periodo[(~df_periodo["ATENDIDO"]) & (~df_periodo["PERDIDO"])].copy()
    if df_nao.empty:
        st.info("Nenhum lead não atendido no período.")
    else:
        df_nao["Captura"] = df_nao["DATA_CAPTURA_DT"].apply(fmt_dt)
        cols = [
            "NOME_LEAD",
            "TELEFONE_LEAD",
            "Corretor responsável",
            "Captura",
            col_situacao,
            col_etapa,
        ]
        cols = [c for c in cols if c in df_nao.columns]
        st.dataframe(df_nao[cols], use_container_width=True)

with aba3:
    df_1contato = df_periodo[
        (df_periodo["ATENDIDO"])
        & (~df_periodo["PERDIDO"])
        & (df_periodo["DATA_ULT_INTERACAO_DT"].isna())
    ].copy()

    if df_1contato.empty:
        st.info("Nenhum lead com apenas 1 contato no período.")
    else:
        df_1contato["Captura"] = df_1contato["DATA_CAPTURA_DT"].apply(fmt_dt)
        df_1contato["1º contato"] = df_1contato["DATA_COM_CORRETOR_DT"].apply(fmt_dt)
        cols = [
            "NOME_LEAD",
            "TELEFONE_LEAD",
            "Corretor responsável",
            "Captura",
            "1º contato",
            col_situacao,
            col_etapa,
        ]
        cols = [c for c in cols if c in df_1contato.columns]
        st.dataframe(df_1contato[cols], use_container_width=True)
