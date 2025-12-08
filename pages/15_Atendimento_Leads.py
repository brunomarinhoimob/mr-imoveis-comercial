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

# Corretor / responsável pelo lead
col_corretor = get_col(
    [
        "nome_corretor_norm",
        "nome_corretor",
        "corretor",
        "responsavel",
        "responsável",
        "usuario_responsavel",
        "usuario",
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

# SLA médio apenas dos atendidos (captura -> primeiro contato)
sla_medio_min = df_periodo.loc[df_periodo["ATENDIDO"], "SLA_MINUTOS"].mean()

# Leads perdidos no período (já calculado acima)
qtde_leads_perdidos_periodo = int(qtde_leads_perdidos_periodo)

# KPI – % de leads atendidos em até 15 minutos
SLA_ALVO_MIN = 15
if leads_atendidos > 0:
    num_ate15 = int(
        (
            df_periodo["ATENDIDO"]
            & (df_periodo["SLA_MINUTOS"] <= SLA_ALVO_MIN)
        ).sum()
    )
    pct_ate15 = (num_ate15 / leads_atendidos) * 100
else:
    num_ate15 = 0
    pct_ate15 = np.nan

# 1ª linha de cards
c1, c2, c3, c4 = st.columns(4)
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

# 2ª linha de cards
r2c1, r2c2, r2c3 = st.columns(3)
with r2c1:
    st.metric("Leads perdidos no período", qtde_leads_perdidos_periodo)
with r2c2:
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
with r2c3:
    if leads_atendidos > 0:
        st.metric(
            "% atendidos em até 15 min",
            f"{pct_ate15:.1f}%",
            help=f"{num_ate15} de {leads_atendidos} leads atendidos no prazo alvo.",
        )
    else:
        st.metric("% atendidos em até 15 min", "-", help="Nenhum lead atendido no período.")

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
# VISÃO POR CORRETOR – Resumo sem ranking
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

df_resumo_corretor = df_cor.groupby("CORRETOR_EXIBICAO", dropna=False).agg(
    LEADS=("NOME_LEAD", "count"),
    ATENDIDOS=("ATENDIDO", "sum"),
    SLA_MEDIO_MIN=("SLA_INICIAL_MIN", "mean"),
    SLA_INTERACOES_MIN=("SLA_INTERACOES_MIN", "mean"),
).reset_index()

# Ordena pelo SLA médio (captura -> 1º contato)
df_resumo_corretor = df_resumo_corretor.sort_values(
    ["SLA_MEDIO_MIN", "CORRETOR_EXIBICAO"], ascending=[True, True]
)

# DataFrame para exibição
df_display = df_resumo_corretor.copy().rename(
    columns={
        "CORRETOR_EXIBICAO": "Corretor",
        "LEADS": "Leads",
        "ATENDIDOS": "Leads atendidos",
        "SLA_MEDIO_MIN": "SLA inicial médio (min)",
        "SLA_INTERACOES_MIN": "SLA interações médio (min)",
    }
)

styler_resumo = df_display.style.format(
    {
        "SLA inicial médio (min)": format_minutes,
        "SLA interações médio (min)": format_minutes,
    }
)

st.subheader("📌 Resumo geral por corretor")
st.dataframe(styler_resumo, hide_index=True, use_container_width=True)

# -------- Download CSV da visão por corretor --------
df_export = df_resumo_corretor.copy().rename(
    columns={
        "CORRETOR_EXIBICAO": "Corretor",
        "LEADS": "Leads",
        "ATENDIDOS": "Leads atendidos",
        "SLA_MEDIO_MIN": "SLA inicial médio (min)",
        "SLA_INTERACOES_MIN": "SLA interações médio (min)",
    }
)
csv_bytes = df_export.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    "⬇️ Baixar resumo por corretor (CSV)",
    data=csv_bytes,
    file_name="resumo_atendimento_por_corretor.csv",
    mime="text/csv",
)

# -------- NOVA TABELA – LEADS DO CORRETOR SELECIONADO (COM TODOS OS CONTATOS) --------
if corretor_sel != "Todos":
    st.markdown("### 📂 Leads do corretor selecionado no período")

    df_corretor = df_cor.copy()  # já está filtrado pelo período e corretor

    if df_corretor.empty:
        st.info("Nenhum lead encontrado para o corretor selecionado nesse período.")
    else:
        # Todas as colunas que têm 'contato' no nome (além das normalizadas)
        contact_cols_all = [
            c for c in df_corretor.columns if "contato" in c.lower()
        ]

        col_first_contact_norm = (
            "DATA_COM_CORRETOR_DT"
            if "DATA_COM_CORRETOR_DT" in df_corretor.columns
            else None
        )

        cols_to_remove = set()
        if col_first_contact_norm:
            cols_to_remove.add(col_first_contact_norm)
        if "DATA_ULT_INTERACAO_DT" in df_corretor.columns:
            cols_to_remove.add("DATA_ULT_INTERACAO_DT")

        extra_contact_cols = [
            c for c in contact_cols_all if c not in cols_to_remove
        ]

        # Monta colunas da tabela detalhada
        cols_det = ["NOME_LEAD", "CORRETOR_EXIBICAO", "DATA_CAPTURA_DT"]
        if col_first_contact_norm:
            cols_det.append(col_first_contact_norm)
        cols_det += extra_contact_cols
        cols_det.append("SLA_INTERACOES_MIN")
        if "DATA_ULT_INTERACAO_DT" in df_corretor.columns:
            cols_det.append("DATA_ULT_INTERACAO_DT")

        cols_det = [c for c in cols_det if c in df_corretor.columns]

        df_det = df_corretor[cols_det].copy()

        # Formata todas as colunas de data/hora (captura, contatos e última interação)
        for c in df_det.columns:
            if "contato" in c.lower() or c in [
                "DATA_CAPTURA_DT",
                "DATA_ULT_INTERACAO_DT",
            ]:
                df_det[c] = pd.to_datetime(df_det[c], errors="coerce").dt.strftime(
                    "%d/%m/%Y %H:%M"
                )

        # SLA entre contatos em formato legível
        if "SLA_INTERACOES_MIN" in df_det.columns:
            df_det["SLA_INTERACOES_MIN"] = df_det["SLA_INTERACOES_MIN"].apply(
                format_minutes
            )

        # Renomeia colunas para exibição
        rename_map = {
            "NOME_LEAD": "Lead",
            "CORRETOR_EXIBICAO": "Corretor",
            "DATA_CAPTURA_DT": "Data captura",
            "DATA_COM_CORRETOR_DT": "Data 1º contato",
            "SLA_INTERACOES_MIN": "SLA entre contatos",
            "DATA_ULT_INTERACAO_DT": "Data última interação",
        }

        # Colunas extras de contato recebem um nome "bonito" automaticamente
        for c in extra_contact_cols:
            pretty = c.replace("_", " ").strip()
            pretty = " ".join(pretty.split())
            pretty = pretty.capitalize()
            rename_map[c] = pretty

        df_det = df_det.rename(columns=rename_map)

        st.dataframe(df_det, use_container_width=True, hide_index=True)

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
        cols_atendidos = [
            "NOME_LEAD",
            "TELEFONE_LEAD",
            "CORRETOR_EXIBICAO",
            "DATA_CAPTURA_DT",
            "DATA_COM_CORRETOR_DT",
            "DATA_ULT_INTERACAO_DT",
        ]
        if col_situacao:
            cols_atendidos.append(col_situacao)
        if col_etapa:
            cols_atendidos.append(col_etapa)

        df_atendidos_tab = df_atendidos[cols_atendidos].copy()

        df_atendidos_tab["DATA_CAPTURA_DT"] = df_atendidos_tab[
            "DATA_CAPTURA_DT"
        ].dt.strftime("%d/%m/%Y %H:%M")
        df_atendidos_tab["DATA_COM_CORRETOR_DT"] = df_atendidos_tab[
            "DATA_COM_CORRETOR_DT"
        ].dt.strftime("%d/%m/%Y %H:%M")
        df_atendidos_tab["DATA_ULT_INTERACAO_DT"] = df_atendidos_tab[
            "DATA_ULT_INTERACAO_DT"
        ].dt.strftime("%d/%m/%Y %H:%M")

        rename_atendidos = {
            "NOME_LEAD": "Lead",
            "TELEFONE_LEAD": "Telefone",
            "CORRETOR_EXIBICAO": "Corretor",
            "DATA_CAPTURA_DT": "Data de captura",
            "DATA_COM_CORRETOR_DT": "1º contato com corretor",
            "DATA_ULT_INTERACAO_DT": "Última interação",
        }
        if col_situacao:
            rename_atendidos[col_situacao] = "Situação"
        if col_etapa:
            rename_atendidos[col_etapa] = "Etapa"

        df_atendidos_tab = df_atendidos_tab.rename(columns=rename_atendidos)

        st.dataframe(df_atendidos_tab, use_container_width=True, hide_index=True)

with aba2:
    st.subheader("⏳ Leads não atendidos no período")

    df_nao_atendidos = df_periodo[~df_periodo["ATENDIDO"]].copy()
    if df_nao_atendidos.empty:
        st.info("Todos os leads do período foram atendidos pelo menos uma vez. 🎉")
    else:
        cols_na = [
            "NOME_LEAD",
            "TELEFONE_LEAD",
            "CORRETOR_EXIBICAO",
            "DATA_CAPTURA_DT",
        ]
        if col_situacao:
            cols_na.append(col_situacao)
        if col_etapa:
            cols_na.append(col_etapa)

        df_nao_atendidos_tab = df_nao_atendidos[cols_na].copy()

        df_nao_atendidos_tab["DATA_CAPTURA_DT"] = df_nao_atendidos_tab[
            "DATA_CAPTURA_DT"
        ].dt.strftime("%d/%m/%Y %H:%M")

        rename_na = {
            "NOME_LEAD": "Lead",
            "TELEFONE_LEAD": "Telefone",
            "CORRETOR_EXIBICAO": "Corretor",
            "DATA_CAPTURA_DT": "Data de captura",
        }
        if col_situacao:
            rename_na[col_situacao] = "Situação"
        if col_etapa:
            rename_na[col_etapa] = "Etapa"

        df_nao_atendidos_tab = df_nao_atendidos_tab.rename(columns=rename_na)

        st.dataframe(df_nao_atendidos_tab, use_container_width=True, hide_index=True)

with aba3:
    st.subheader("📞 Leads com apenas 1 contato")

    # Aqui NÃO consideramos leads perdidos: apenas leads ativos
    df_1_contato = df_periodo[
        (~df_periodo["PERDIDO"])
        & df_periodo["ATENDIDO"]
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
        st.info("Nenhum lead ativo ficou com apenas um contato no período. 👏")
    else:
        cols_1c = [
            "NOME_LEAD",
            "TELEFONE_LEAD",
            "CORRETOR_EXIBICAO",
            "DATA_COM_CORRETOR_DT",
        ]
        if col_situacao:
            cols_1c.append(col_situacao)
        if col_etapa:
            cols_1c.append(col_etapa)

        df_tab_1c = df_1_contato[cols_1c].copy()
        rename_1c = {
            "NOME_LEAD": "Lead",
            "TELEFONE_LEAD": "Telefone",
            "CORRETOR_EXIBICAO": "Corretor",
            "DATA_COM_CORRETOR_DT": "Data do único contato",
        }
        if col_situacao:
            rename_1c[col_situacao] = "Situação"
        if col_etapa:
            rename_1c[col_etapa] = "Etapa"

        df_tab_1c = df_tab_1c.rename(columns=rename_1c)
        df_tab_1c["Data do único contato"] = pd.to_datetime(
            df_tab_1c["Data do único contato"], errors="coerce"
        ).dt.strftime("%d/%m/%Y %H:%M")
        st.dataframe(df_tab_1c, use_container_width=True, hide_index=True)
