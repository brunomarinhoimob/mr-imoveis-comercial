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
# Nome do lead
col_nome = None
for c in ["nome_pessoa", "nome", "nome_cliente"]:
    if c in df.columns:
        col_nome = c
        break

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
col_tel = None
for c in ["telefone_pessoa", "telefone", "phone"]:
    if c in df.columns:
        col_tel = c
        break

if col_tel is None:
    df["TELEFONE_LEAD"] = ""
else:
    df["TELEFONE_LEAD"] = df[col_tel].fillna("").astype(str).str.strip()

# Corretor
col_corretor = None
for c in ["nome_corretor_norm", "nome_corretor"]:
    if c in df.columns:
        col_corretor = c
        break

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
col_situacao = "nome_situacao" if "nome_situacao" in df.columns else None
col_etapa = "nome_etapa" if "nome_etapa" in df.columns else None

# Datas principais
if "data_captura" in df.columns:
    df["DATA_CAPTURA_DT"] = pd.to_datetime(df["data_captura"], errors="coerce")
else:
    df["DATA_CAPTURA_DT"] = pd.NaT

if "data_com_corretor" in df.columns:
    df["DATA_COM_CORRETOR_DT"] = pd.to_datetime(df["data_com_corretor"], errors="coerce")
else:
    df["DATA_COM_CORRETOR_DT"] = pd.NaT

if "data_ultimo_atendimento" in df.columns:
    df["DATA_ULT_INTERACAO_DT"] = pd.to_datetime(
        df["data_ultimo_atendimento"], errors="coerce"
    )
else:
    df["DATA_ULT_INTERACAO_DT"] = pd.NaT

if "data_vendendo" in df.columns:
    df["DATA_VENDENDO_DT"] = pd.to_datetime(df["data_vendendo"], errors="coerce")
else:
    df["DATA_VENDENDO_DT"] = pd.NaT

if "data_vendido_perdido" in df.columns:
    df["DATA_VENDIDO_PERDIDO_DT"] = pd.to_datetime(df["data_vendido_perdido"], errors="coerce")
else:
    df["DATA_VENDIDO_PERDIDO_DT"] = pd.NaT

# remove linhas sem captura
df = df[df["DATA_CAPTURA_DT"].notna()].copy()
if df.empty:
    st.error("Não há leads com data de captura válida.")
    st.stop()

# ---------------------------------------------------------
# AUXILIARES
# ---------------------------------------------------------
def format_minutes(total_min):
    if pd.isna(total_min):
        return "-"
    total_min = int(total_min)
    horas = total_min // 60
    minutos = total_min % 60
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

if data_ini > data_fim:
    data_ini, data_fim = data_fim, data_ini

# Filtro por corretor
lista_corretor = sorted(df["CORRETOR_EXIBICAO"].dropna().unique())
corretor_sel = st.sidebar.selectbox(
    "Filtrar por corretor (opcional)",
    ["Todos"] + lista_corretor,
)

# ---------------------------------------------------------
# APLICAÇÃO DOS FILTROS NA BASE
# ---------------------------------------------------------
mask_periodo = (df["DATA_CAPTURA_DT"].dt.date >= data_ini) & (
    df["DATA_CAPTURA_DT"].dt.date <= data_fim
)
df_periodo = df[mask_periodo].copy()

if corretor_sel != "Todos":
    df_periodo = df_periodo[df_periodo["CORRETOR_EXIBICAO"] == corretor_sel]

if df_periodo.empty:
    st.warning("Nenhum lead encontrado para os filtros selecionados.")
    st.stop()

# lead atendido = tem DATA_COM_CORRETOR_DT
df_periodo["ATENDIDO"] = df_periodo["DATA_COM_CORRETOR_DT"].notna()

# SLA = tempo entre CAPTURA e DATA_COM_CORRETOR_DT (apenas atendidos)
mask_sla = df_periodo["ATENDIDO"] & df_periodo["DATA_COM_CORRETOR_DT"].notna()
df_sla = df_periodo[mask_sla].copy()
df_sla["SLA_MIN"] = (
    (df_sla["DATA_COM_CORRETOR_DT"] - df_sla["DATA_CAPTURA_DT"])
    .dt.total_seconds()
    .div(60)
)

sla_medio_min = df_sla["SLA_MIN"].mean() if not df_sla.empty else np.nan

# Leads com perda
mask_perdido = df["DATA_VENDIDO_PERDIDO_DT"].notna()
df_perdidos = df[mask_perdido].copy()

qtde_leads_periodo = len(df_periodo)

# mesma lógica para perdidos (para usar no card)
qtde_leads_perdidos_periodo = 0
if not df_perdidos.empty:
    mask_perdido_periodo = (df_perdidos["DATA_CAPTURA_DT"].dt.date >= data_ini) & (
        df_perdidos["DATA_CAPTURA_DT"].dt.date <= data_fim
    )
    df_perdidos_periodo = df_perdidos[mask_perdido_periodo].copy()
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

    df_busca_tab["DATA_CAPTURA_DT"] = df_busca_tab["DATA_CAPTURA_DT"].dt.strftime(
        "%d/%m/%Y %H:%M"
    )
    df_busca_tab["DATA_COM_CORRETOR_DT"] = df_busca_tab[
        "DATA_COM_CORRETOR_DT"
    ].dt.strftime("%d/%m/%Y %H:%M")
    df_busca_tab["DATA_ULT_INTERACAO_DT"] = df_busca_tab[
        "DATA_ULT_INTERACAO_DT"
    ].dt.strftime("%d/%m/%Y %H:%M")

    df_busca_tab = df_busca_tab.rename(
        columns={
            "NOME_LEAD": "Lead",
            "TELEFONE_LEAD": "Telefone",
            "CORRETOR_EXIBICAO": "Corretor",
            "DATA_CAPTURA_DT": "Data captura",
            "DATA_COM_CORRETOR_DT": "Data com corretor",
            "DATA_ULT_INTERACAO_DT": "Última interação",
            col_situacao: "Situação" if col_situacao else col_situacao,
            col_etapa: "Etapa" if col_etapa else col_etapa,
        }
    )

    st.dataframe(df_busca_tab, use_container_width=True, hide_index=True)
else:
    if nome_busca.strip():
        st.info("Nenhum lead encontrado com esse nome no período filtrado.")

# ---------------------------------------------------------
# VISÃO DETALHADA POR STATUS DE ATENDIMENTO
# ---------------------------------------------------------
st.markdown("---")
st.markdown("## 📊 Detalhamento do atendimento")

aba1, aba2, aba3 = st.tabs(
    ["Leads atendidos", "Leads não atendidos", "Leads sem retorno"]
)

# ------------------------------------
# 1) LEADS ATENDIDOS
# ------------------------------------
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
                "DATA_CAPTURA_DT": "Data captura",
                "DATA_COM_CORRETOR_DT": "Data com corretor",
                "DATA_ULT_INTERACAO_DT": "Última interação",
                col_situacao: "Situação" if col_situacao else col_situacao,
                col_etapa: "Etapa" if col_etapa else col_etapa,
            }
        )

        st.dataframe(df_atendidos_tab, use_container_width=True, hide_index=True)

# ------------------------------------
# 2) LEADS NÃO ATENDIDOS
# ------------------------------------
with aba2:
    st.subheader("⏱️ Leads não atendidos")

    df_nao_atendidos = df_periodo[~df_periodo["ATENDIDO"]].copy()
    if df_nao_atendidos.empty:
        st.info("Nenhum lead não atendido no período.")
    else:
        df_nao_tab = df_nao_atendidos[
            [
                "NOME_LEAD",
                "TELEFONE_LEAD",
                "CORRETOR_EXIBICAO",
                "DATA_CAPTURA_DT",
                "DATA_ULT_INTERACAO_DT",
            ]
            + ([col_situacao] if col_situacao else [])
            + ([col_etapa] if col_etapa else [])
        ].copy()

        df_nao_tab["DATA_CAPTURA_DT"] = df_nao_tab["DATA_CAPTURA_DT"].dt.strftime(
            "%d/%m/%Y %H:%M"
        )
        df_nao_tab["DATA_ULT_INTERACAO_DT"] = df_nao_tab[
            "DATA_ULT_INTERACAO_DT"
        ].dt.strftime("%d/%m/%Y %H:%M")

        df_nao_tab = df_nao_tab.rename(
            columns={
                "NOME_LEAD": "Lead",
                "TELEFONE_LEAD": "Telefone",
                "CORRETOR_EXIBICAO": "Corretor",
                "DATA_CAPTURA_DT": "Data captura",
                "DATA_ULT_INTERACAO_DT": "Última interação",
                col_situacao: "Situação" if col_situacao else col_situacao,
                col_etapa: "Etapa" if col_etapa else col_etapa,
            }
        )

        st.dataframe(df_nao_tab, use_container_width=True, hide_index=True)

# ------------------------------------
# 3) LEADS SEM RETORNO (APENAS 1 CONTATO)
# ------------------------------------
with aba3:
    st.subheader("🔁 Leads sem retorno (apenas 1 contato)")

    # Se não tem DATA_COM_CORRETOR_DT -> 0 contatos
    # Se tem DATA_COM_CORRETOR_DT mas não tem DATA_ULT_INTERACAO_DT -> 1 contato
    df_1c = df_periodo.copy()
    cond_sem_atendimento = df_1c["DATA_COM_CORRETOR_DT"].isna()
    cond_um_contato = df_1c["DATA_COM_CORRETOR_DT"].notna() & df_1c[
        "DATA_ULT_INTERACAO_DT"
    ].isna()

    df_1c = df_1c[cond_um_contato].copy()

    if df_1c.empty:
        st.info("Nenhum lead com apenas 1 contato no período.")
    else:
        df_tab_1c = df_1c[
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
