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

# Logo MR Imóveis na lateral
try:
    st.sidebar.image("logo_mr.png", use_container_width=True)
except Exception:
    pass

st.title("📞 Controle de Atendimento de Leads")
st.caption(
    "Visão simples e operacional do atendimento: leads atendidos, não atendidos, SLA e leads sem retorno."
)

# ---------------------------------------------------------
# BUSCA LEADS DO SESSION_STATE
# ---------------------------------------------------------
df_leads = st.session_state.get("df_leads", pd.DataFrame())

if df_leads is None or df_leads.empty:
    st.error(
        "Nenhum dado de leads encontrado. "
        "Abra primeiro a página principal (app_dashboard.py) para carregar os leads do Supremo."
    )
    st.stop()

df = df_leads.copy()

# ---------------------------------------------------------
# NORMALIZAÇÃO DE COLUNAS
# ---------------------------------------------------------

# Mapa auxiliar para localizar colunas de forma case-insensitive
lower_cols = {c.lower(): c for c in df.columns}

def get_col(possiveis_nomes):
    """
    Recebe uma lista de nomes (em minúsculo) e devolve
    o nome real da coluna no DF (preservando maiúsculas/minúsculas).
    """
    for nome in possiveis_nomes:
        if nome in lower_cols:
            return lower_cols[nome]
    return None

# Nome do lead
col_nome = get_col(
    [
        "nome_pessoa",
        "nome",
        "nome_lead",
        "nome_cliente",
        "cliente",
        "pessoa",
        "nome do cliente",
    ]
)

if col_nome is None:
    df["NOME_LEAD"] = "SEM NOME"
else:
    df["NOME_LEAD"] = (
        df[col_nome]
        .fillna("SEM NOME")
        .astype(str)
        .str.strip()
        .replace("", "SEM NOME")
    )

# Telefone
col_tel = get_col(
    [
        "telefone",
        "telefone1",
        "telefone_principal",
        "celular",
        "whatsapp",
        "whats_app",
        "fone",
    ]
)

if col_tel is None:
    df["TELEFONE_LEAD"] = ""
else:
    df["TELEFONE_LEAD"] = df[col_tel].fillna("").astype(str).str.strip()

# Corretor
col_corretor = get_col(
    [
        "nome_corretor_norm",
        "nome_corretor",
        "corretor",
        "responsavel",
        "responsável",
    ]
)

if col_corretor is None:
    df["CORRETOR_EXIBICAO"] = "SEM CORRETOR"
else:
    df["CORRETOR_EXIBICAO"] = (
        df[col_corretor]
        .fillna("SEM CORRETOR")
        .astype(str)
        .str.strip()
        .replace("", "SEM CORRETOR")
    )

# Situação / etapa
col_situacao = get_col(["nome_situacao", "situacao", "situação"])
col_etapa = get_col(["nome_etapa", "etapa"])

# Datas principais
col_data_captura = get_col(["data_captura", "data do lead", "data_lead"])
if col_data_captura:
    df["DATA_CAPTURA_DT"] = pd.to_datetime(df[col_data_captura], errors="coerce")
else:
    df["DATA_CAPTURA_DT"] = pd.NaT

col_data_com_corretor = get_col(["data_com_corretor", "data_primeiro_atendimento"])
if col_data_com_corretor:
    df["DATA_COM_CORRETOR_DT"] = pd.to_datetime(
        df[col_data_com_corretor], errors="coerce"
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
    df.loc[
        situ_norm.str.contains("PERD", na=False)
        | situ_norm.str.contains("DESCART", na=False)
        | situ_norm.str.contains("NÃO TEM INTERESSE", na=False)
        | situ_norm.str.contains("NAO TEM INTERESSE", na=False),
        "PERDIDO",
    ] = True

if col_etapa:
    etapa_norm = df[col_etapa].fillna("").astype(str).str.upper()
    df.loc[
        etapa_norm.str.contains("PERD", na=False)
        | etapa_norm.str.contains("DESCART", na=False),
        "PERDIDO",
    ] = True

# ATENDIDO = já teve contato com corretor
df["ATENDIDO"] = df["DATA_COM_CORRETOR_DT"].notna()

# SLA EM MINUTOS – tempo entre captura e primeiro contato
df["SLA_MINUTOS"] = np.where(
    df["DATA_COM_CORRETOR_DT"].notna(),
    (df["DATA_COM_CORRETOR_DT"] - df["DATA_CAPTURA_DT"]).dt.total_seconds() / 60,
    np.nan,
)


# Função utilitária para formatar minutos como "Xh YYmin"
def format_minutes(total_min):
    if pd.isna(total_min):
        return "-"
    total_min = int(total_min)
    horas = total_min // 60
    minutos = total_min % 60
    if horas == 0:
        return f"{minutos} min"
    return f"{horas}h {minutos:02d} min"


def fmt_dt(dt):
    if pd.isna(dt):
        return "-"
    return pd.to_datetime(dt).strftime("%d/%m/%Y %H:%M")


# ---------------------------------------------------------
# FILTROS LATERAIS
# ---------------------------------------------------------
st.sidebar.title("Filtros – Atendimento")

# Período
data_min = df["DATA_CAPTURA_DT"].min().date()
data_max = df["DATA_CAPTURA_DT"].max().date()
default_ini = max(data_min, data_max - timedelta(days=7))

periodo = st.sidebar.date_input(
    "Período (data de captura do lead)",
    value=(default_ini, data_max),
    min_value=data_min,
    max_value=data_max,
)

if isinstance(periodo, tuple) and len(periodo) == 2:
    data_ini, data_fim = periodo
else:
    data_ini = periodo
    data_fim = periodo

# Filtro de corretor
lista_corretores = sorted(df["CORRETOR_EXIBICAO"].unique())
corretor_sel = st.sidebar.selectbox("Corretor", ["Todos"] + lista_corretores)

# ---------------------------------------------------------
# APLICA FILTROS
# ---------------------------------------------------------
mask_periodo = (df["DATA_CAPTURA_DT"].dt.date >= data_ini) & (
    df["DATA_CAPTURA_DT"].dt.date <= data_fim
)
df_periodo = df[mask_periodo].copy()

if corretor_sel != "Todos":
    df_periodo = df_periodo[df_periodo["CORRETOR_EXIBICAO"] == corretor_sel]

qtde_leads_periodo = len(df_periodo)

if qtde_leads_periodo == 0:
    st.warning("Nenhum lead encontrado para os filtros selecionados.")
    st.stop()

# Leads perdidos no período (antes de filtrar por corretor, para visão geral)
df_perdidos_periodo = df[mask_periodo & df["PERDIDO"]].copy()
qtde_leads_perdidos_periodo = len(df_perdidos_periodo)
if corretor_sel != "Todos":
    df_perdidos_periodo = df_perdidos_periodo[
        df_perdidos_periodo["CORRETOR_EXIBICAO"] == corretor_sel
    ]
    qtde_leads_perdidos_periodo = len(df_perdidos_periodo)

st.caption(
    f"Período: **{data_ini.strftime('%d/%m/%Y')}** até **{data_fim.strftime('%d/%m/%Y')}** "
    f"• Leads no período (sem perdidos): **{qtde_leads_periodo}**"
    + (f" • Corretor: **{corretor_sel}**" if corretor_sel != "Todos" else "")
)

# ---------------------------------------------------------
# VISÃO GERAL (CARDS)
# ---------------------------------------------------------
leads_atendidos = int(df_periodo["ATENDIDO"].sum())
leads_nao_atendidos = int(qtde_leads_periodo - leads_atendidos)

st.markdown("## 🧾 Visão geral do atendimento")

# Leads novos = leads no período que ainda não foram encaminhados para corretor
mask_leads_novos = (
    df_periodo["CORRETOR_EXIBICAO"].eq("SEM CORRETOR")
    & df_periodo["DATA_COM_CORRETOR_DT"].isna()
)
qtde_leads_novos = int(mask_leads_novos.sum())

# SLA médio apenas dos atendidos
sla_medio_min = df_periodo.loc[df_periodo["ATENDIDO"], "SLA_MINUTOS"].mean()

# Leads perdidos no período (já calculado acima)
qtde_leads_perdidos_periodo = int(qtde_leads_perdidos_periodo)

c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1:
    st.metric("Leads no período", qtde_leads_periodo)
with c2:
    st.metric("Leads atendidos", leads_atendidos)
with c3:
    st.metric("Leads não atendidos", leads_nao_atendidos)
with c4:
    st.metric(
        "SLA médio (leads atendidos)",
        format_minutes(sla_medio_min) if leads_atendidos > 0 else "-",
    )
with c5:
    st.metric("Leads perdidos no período", qtde_leads_perdidos_periodo)
with c6:
    if qtde_leads_novos > 0:
        st.metric(
            "📥 Leads novos",
            qtde_leads_novos,
            delta="Precisa distribuir",
            delta_color="inverse",
        )
    else:
        st.metric(
            "📥 Leads novos",
            qtde_leads_novos,
            delta="Nenhum lead novo",
            delta_color="off",
        )

# Se houver leads novos, mostra um resumo logo abaixo
if qtde_leads_novos > 0:
    df_leads_novos = df_periodo[mask_leads_novos].copy()
    st.warning(
        f"Existem **{qtde_leads_novos}** lead(s) novo(s) sem corretor. "
        "Distribua o quanto antes para não perder oportunidade."
    )
    with st.expander("Ver leads novos (sem corretor)"):
        colunas_novos = ["NOME_LEAD", "TELEFONE_LEAD", "DATA_CAPTURA_DT"]
        colunas_existentes = [c for c in colunas_novos if c in df_leads_novos.columns]
        df_novos_tab = df_leads_novos[colunas_existentes].copy()
        if "DATA_CAPTURA_DT" in df_novos_tab.columns:
            df_novos_tab["DATA_CAPTURA_DT"] = pd.to_datetime(
                df_novos_tab["DATA_CAPTURA_DT"], errors="coerce"
            ).dt.strftime("%d/%m/%Y %H:%M")
        df_novos_tab = df_novos_tab.rename(
            columns={
                "NOME_LEAD": "Lead",
                "TELEFONE_LEAD": "Telefone",
                "DATA_CAPTURA_DT": "Data de captura",
            }
        )
        st.dataframe(df_novos_tab, use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# VISÃO POR CORRETOR – Tabela Resumo + Tabela Detalhada
# ---------------------------------------------------------
st.markdown("---")
st.markdown("## 👥 Desempenho por corretor")

df_cor = df_periodo.copy()

# SLA inicial: tempo entre captura do lead e primeiro atendimento
df_cor["SLA_INICIAL_MIN"] = np.where(
    df_cor["DATA_COM_CORRETOR_DT"].notna(),
    (df_cor["DATA_COM_CORRETOR_DT"] - df_cor["DATA_CAPTURA_DT"])
    .dt.total_seconds() / 60,
    np.nan,
)

# SLA entre interações: tempo entre o primeiro atendimento e a última interação
df_cor["SLA_INTERACOES_MIN"] = np.where(
    df_cor["DATA_COM_CORRETOR_DT"].notna() & df_cor["DATA_ULT_INTERACAO_DT"].notna(),
    (df_cor["DATA_ULT_INTERACAO_DT"] - df_cor["DATA_COM_CORRETOR_DT"])
    .dt.total_seconds() / 60,
    np.nan,
)

# ---------- TABELA RESUMO ----------
df_resumo_corretor = df_cor.groupby("CORRETOR_EXIBICAO").agg(
    LEADS=("NOME_LEAD", "count"),
    ATENDIDOS=("ATENDIDO", "sum"),
    SLA_MEDIO=("SLA_INICIAL_MIN", "mean"),
    SLA_INTERACOES_MEDIO=("SLA_INTERACOES_MIN", "mean"),
).reset_index()

df_resumo_corretor["SLA_MEDIO"] = df_resumo_corretor["SLA_MEDIO"].apply(format_minutes)
df_resumo_corretor["SLA_INTERACOES_MEDIO"] = df_resumo_corretor[
    "SLA_INTERACOES_MEDIO"
].apply(format_minutes)

df_resumo_corretor = df_resumo_corretor.rename(
    columns={
        "CORRETOR_EXIBICAO": "Corretor",
        "LEADS": "Leads",
        "ATENDIDOS": "Leads atendidos",
        "SLA_MEDIO": "SLA inicial médio",
        "SLA_INTERACOES_MEDIO": "SLA entre interações (médio)",
    }
).sort_values("Leads", ascending=False)

st.subheader("📌 Resumo geral por corretor")
st.dataframe(df_resumo_corretor, hide_index=True, use_container_width=True)

# ---------- TABELA DETALHADA (COM NOMES) ----------
st.subheader("📄 Lista completa de leads por corretor")

df_detalhe = df_cor[
    [
        "CORRETOR_EXIBICAO",
        "NOME_LEAD",
        "TELEFONE_LEAD",
        "DATA_CAPTURA_DT",
        "DATA_COM_CORRETOR_DT",
        "DATA_ULT_INTERACAO_DT",
        "SLA_INICIAL_MIN",
        "SLA_INTERACOES_MIN",
    ]
    + ([col_situacao] if col_situacao else [])
    + ([col_etapa] if col_etapa else [])
].copy()

df_detalhe["DATA_CAPTURA_DT"] = df_detalhe["DATA_CAPTURA_DT"].apply(fmt_dt)
df_detalhe["DATA_COM_CORRETOR_DT"] = df_detalhe["DATA_COM_CORRETOR_DT"].apply(fmt_dt)
df_detalhe["DATA_ULT_INTERACAO_DT"] = df_detalhe[
    "DATA_ULT_INTERACAO_DT"
].apply(fmt_dt)

df_detalhe["SLA_INICIAL"] = df_detalhe["SLA_INICIAL_MIN"].apply(format_minutes)
df_detalhe["SLA_INTERACOES"] = df_detalhe["SLA_INTERACOES_MIN"].apply(format_minutes)

df_detalhe = df_detalhe.rename(
    columns={
        "CORRETOR_EXIBICAO": "Corretor",
        "NOME_LEAD": "Lead",
        "TELEFONE_LEAD": "Telefone",
        "DATA_CAPTURA_DT": "Captura",
        "DATA_COM_CORRETOR_DT": "1º Contato",
        "DATA_ULT_INTERACAO_DT": "Última Interação",
        "SLA_INICIAL": "SLA inicial",
        "SLA_INTERACOES": "SLA interações",
        col_situacao: "Situação" if col_situacao else col_situacao,
        col_etapa: "Etapa" if col_etapa else col_etapa,
    }
)

st.dataframe(df_detalhe, hide_index=True, use_container_width=True)

# ---------------------------------------------------------
# BUSCAR LEAD ESPECÍFICO
# ---------------------------------------------------------
st.markdown("---")
st.markdown("## 🔎 Buscar lead específico")

nome_busca = st.text_input(
    "Digite parte do nome do lead para localizar",
    value="",
    placeholder="Ex.: Maria, João, Silva...",
)

df_busca = df_periodo.copy()
if nome_busca.strip():
    termo = nome_busca.strip().upper()
    df_busca = df_busca[df_busca["NOME_LEAD"].str.upper().str.contains(termo)]

if not df_busca.empty:
    df_busca_tab = df_busca[
        [
            "NOME_LEAD",
            "TELEFONE_LEAD",
            "CORRETOR_EXIBICAO",
            "DATA_CAPTURA_DT",
            "DATA_COM_CORRETOR_DT",
            "DATA_ULT_INTERACAO_DT",
        ]
        + ([col_situacao] if col_situacao else [])
        + ([col_etapa] if col_etapa else [])
    ].copy()

    df_busca_tab["DATA_CAPTURA_DT"] = df_busca_tab["DATA_CAPTURA_DT"].apply(fmt_dt)
    df_busca_tab["DATA_COM_CORRETOR_DT"] = df_busca_tab[
        "DATA_COM_CORRETOR_DT"
    ].apply(fmt_dt)
    df_busca_tab["DATA_ULT_INTERACAO_DT"] = df_busca_tab[
        "DATA_ULT_INTERACAO_DT"
    ].apply(fmt_dt)

    df_busca_tab = df_busca_tab.rename(
        columns={
            "NOME_LEAD": "Lead",
            "TELEFONE_LEAD": "Telefone",
            "CORRETOR_EXIBICAO": "Corretor",
            "DATA_CAPTURA_DT": "Data de captura",
            "DATA_COM_CORRETOR_DT": "1º contato com corretor",
            "DATA_ULT_INTERACAO_DT": "Última interação",
            col_situacao: "Situação" if col_situacao else col_situacao,
            col_etapa: "Etapa" if col_etapa else col_etapa,
        }
    )

    st.dataframe(df_busca_tab, use_container_width=True, hide_index=True)
else:
    if nome_busca.strip():
        st.info("Nenhum lead encontrado com esse nome nos filtros selecionados.")

# ---------------------------------------------------------
# TABELAS DETALHADAS – ATENDIDOS X NÃO ATENDIDOS
# ---------------------------------------------------------
st.markdown("---")
st.markdown("## 📋 Detalhamento dos leads do período")

aba1, aba2, aba3 = st.tabs(
    ["✅ Atendidos", "⏳ Não atendidos", "📞 Apenas 1 contato"]
)

with aba1:
    st.subheader("✅ Leads atendidos no período")

    df_atendidos = df_periodo[df_periodo["ATENDIDO"]].copy()
    if df_atendidos.empty:
        st.info("Nenhum lead atendido no período.")
    else:
        df_atendidos_tab = df_atendidos[
            [
                "NOME_LEAD",
                "TELEFONE_LEAD",
                "CORRETOR_EXIBICAO",
                "DATA_CAPTURA_DT",
                "DATA_COM_CORRETOR_DT",
                "DATA_ULT_INTERACAO_DT",
            ]
            + ([col_situacao] if col_situacao else [])
            + ([col_etapa] if col_etapa else [])
        ].copy()

        df_atendidos_tab["DATA_CAPTURA_DT"] = df_atendidos_tab[
            "DATA_CAPTURA_DT"
        ].dt.strftime("%d/%m/%Y %H:%M")
        df_atendidos_tab["DATA_COM_CORRETOR_DT"] = df_atendidos_tab[
            "DATA_COM_CORRETOR_DT"
        ].dt.strftime("%d/%m/%Y %H:%M")
        df_atendidos_tab["DATA_ULT_INTERACAO_DT"] = df_atendidos_tab[
            "DATA_ULT_INTERACAO_DT"
        ].dt.strftime("%d/%m/%Y %H:%M")

        df_atendidos_tab = df_atendidos_tab.rename(
            columns={
                "NOME_LEAD": "Lead",
                "TELEFONE_LEAD": "Telefone",
                "CORRETOR_EXIBICAO": "Corretor",
                "DATA_CAPTURA_DT": "Data de captura",
                "DATA_COM_CORRETOR_DT": "1º contato com corretor",
                "DATA_ULT_INTERACAO_DT": "Última interação",
                col_situacao: "Situação" if col_situacao else col_situacao,
                col_etapa: "Etapa" if col_etapa else col_etapa,
            }
        )

        st.dataframe(df_atendidos_tab, use_container_width=True, hide_index=True)

with aba2:
    st.subheader("⏳ Leads não atendidos no período")

    df_nao_atendidos = df_periodo[~df_periodo["ATENDIDO"]].copy()
    if df_nao_atendidos.empty:
        st.info("Todos os leads do período foram atendidos pelo menos uma vez. 🎉")
    else:
        df_nao_atendidos_tab = df_nao_atendidos[
            [
                "NOME_LEAD",
                "TELEFONE_LEAD",
                "CORRETOR_EXIBICAO",
                "DATA_CAPTURA_DT",
            ]
            + ([col_situacao] if col_situacao else [])
            + ([col_etapa] if col_etapa else [])
        ].copy()

        df_nao_atendidos_tab["DATA_CAPTURA_DT"] = df_nao_atendidos_tab[
            "DATA_CAPTURA_DT"
        ].dt.strftime("%d/%m/%Y %H:%M")

        df_nao_atendidos_tab = df_nao_atendidos_tab.rename(
            columns={
                "NOME_LEAD": "Lead",
                "TELEFONE_LEAD": "Telefone",
                "CORRETOR_EXIBICAO": "Corretor",
                "DATA_CAPTURA_DT": "Data de captura",
                col_situacao: "Situação" if col_situacao else col_situacao,
                col_etapa: "Etapa" if col_etapa else col_etapa,
            }
        )

        st.dataframe(df_nao_atendidos_tab, use_container_width=True, hide_index=True)

with aba3:
    st.subheader("📞 Leads com apenas 1 contato")

    df_1_contato = df_periodo[
        df_periodo["ATENDIDO"]
        & df_periodo["DATA_COM_CORRETOR_DT"].notna()
        & (
            df_periodo["DATA_ULT_INTERACAO_DT"].isna()
            | (
                df_periodo["DATA_COM_CORRETOR_DT"].notna()
                & df_periodo["DATA_ULT_INTERACAO_DT"].notna()
                & (
                    df_periodo["DATA_COM_CORRETOR_DT"]
                    == df_periodo["DATA_ULT_INTERACAO_DT"]
                )
            )
        )
    ].copy()

    if df_1_contato.empty:
        st.info("Nenhum lead ficou com apenas um contato no período. 👏")
    else:
        df_tab_1c = df_1_contato[
            [
                "NOME_LEAD",
                "TELEFONE_LEAD",
                "CORRETOR_EXIBICAO",
                "DATA_COM_CORRETOR_DT",
            ]
            + ([col_situacao] if col_situacao else [])
            + ([col_etapa] if col_etapa else [])
        ].copy()
        df_tab_1c = df_tab_1c.rename(
            columns={
                "NOME_LEAD": "Lead",
                "TELEFONE_LEAD": "Telefone",
                "CORRETOR_EXIBICAO": "Corretor",
                "DATA_COM_CORRETOR_DT": "Data do único contato",
                col_situacao: "Situação" if col_situacao else col_situacao,
                col_etapa: "Etapa" if col_etapa else col_etapa,
            }
        )
        df_tab_1c["Data do único contato"] = pd.to_datetime(
            df_tab_1c["Data do único contato"], errors="coerce"
        ).dt.strftime("%d/%m/%Y %H:%M")
        st.dataframe(df_tab_1c, use_container_width=True, hide_index=True)
