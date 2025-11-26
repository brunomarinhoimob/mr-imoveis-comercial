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
# BUSCA BASE DE LEADS DO SESSION_STATE
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
    df["NOME_LEAD"] = df[col_nome].fillna("SEM NOME").astype(str).str.strip()

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

# Origem / campanha / situação / etapa
col_origem = "nome_origem" if "nome_origem" in df.columns else None
col_campanha = "nome_campanha" if "nome_campanha" in df.columns else None
col_situacao = "nome_situacao" if "nome_situacao" in df.columns else None
col_etapa = "nome_etapa" if "nome_etapa" in df.columns else None

# Campo de observação para mostrar na ficha do lead
col_descricao = None
for c in ["anotacoes", "interesses", "descricao"]:
    if c in df.columns:
        col_descricao = c
        break

# ---------------------------------------------------------
# DATAS IMPORTANTES
# ---------------------------------------------------------
# captura
if "data_captura_date" in df.columns:
    df["DATA_CAPTURA_DT"] = pd.to_datetime(df["data_captura_date"], errors="coerce")
elif "data_captura" in df.columns:
    df["DATA_CAPTURA_DT"] = pd.to_datetime(df["data_captura"], errors="coerce")
else:
    df["DATA_CAPTURA_DT"] = pd.NaT

# com corretor (primeiro atendimento)
if "data_com_corretor" in df.columns:
    df["DATA_COM_CORRETOR_DT"] = pd.to_datetime(df["data_com_corretor"], errors="coerce")
else:
    df["DATA_COM_CORRETOR_DT"] = pd.NaT

# última interação
if "data_ultima_interacao" in df.columns:
    df["DATA_ULT_INTERACAO_DT"] = pd.to_datetime(df["data_ultima_interacao"], errors="coerce")
else:
    df["DATA_ULT_INTERACAO_DT"] = pd.NaT

# vendendo / vendido_perdido
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
# SEPARA E REMOVER LEADS PERDIDOS (MAS GUARDA PARA CONTAGEM)
# ---------------------------------------------------------
df_perdidos = pd.DataFrame()
if col_situacao or col_etapa:
    mask_perdido = pd.Series(False, index=df.index)
    if col_situacao:
        mask_perdido = mask_perdido | df[col_situacao].astype(str).str.contains(
            "PERDID", case=False, na=False
        )
    if col_etapa:
        mask_perdido = mask_perdido | df[col_etapa].astype(str).str.contains(
            "PERDID", case=False, na=False
        )

    df_perdidos = df[mask_perdido].copy()
    df = df[~mask_perdido].copy()

# ---------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------
def format_minutes(m):
    if pd.isna(m):
        return "-"
    m_int = int(round(m))
    horas = m_int // 60
    minutos = m_int % 60
    if horas <= 0:
        return f"{minutos} min"
    return f"{horas}h {minutos} min"


def fmt_dt(dt_value):
    if pd.isna(dt_value):
        return "-"
    return dt_value.strftime("%d/%m/%Y %H:%M")


# ---------------------------------------------------------
# FILTROS LATERAIS
# ---------------------------------------------------------
st.sidebar.title("Filtros 🔍")

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

# filtro de corretor
lista_corretor = sorted(df["CORRETOR_EXIBICAO"].dropna().unique())
corretor_sel = st.sidebar.selectbox("Corretor", ["Todos"] + lista_corretor)

dias_sem_retorno = st.sidebar.slider(
    "Leads sem retorno há (dias) ou mais",
    min_value=1,
    max_value=30,
    value=3,
    step=1,
)

# aplica filtros
mask_periodo = (df["DATA_CAPTURA_DT"].dt.date >= data_ini) & (
    df["DATA_CAPTURA_DT"].dt.date <= data_fim
)
df_periodo = df[mask_periodo].copy()
if corretor_sel != "Todos":
    df_periodo = df_periodo[df_periodo["CORRETOR_EXIBICAO"] == corretor_sel]

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

if df_periodo.empty:
    st.warning("Nenhum lead encontrado para os filtros selecionados.")
    st.stop()

# ---------------------------------------------------------
# CÁLCULOS PRINCIPAIS
# ---------------------------------------------------------
# lead atendido = tem DATA_COM_CORRETOR_DT
df_periodo["ATENDIDO"] = df_periodo["DATA_COM_CORRETOR_DT"].notna()
leads_atendidos = int(df_periodo["ATENDIDO"].sum())
leads_nao_atendidos = int(qtde_leads_periodo - leads_atendidos)

# SLA em minutos (captura -> com corretor)
df_periodo["SLA_MIN"] = np.nan
mask_sla = df_periodo["ATENDIDO"]
df_periodo.loc[mask_sla, "SLA_MIN"] = (
    df_periodo.loc[mask_sla, "DATA_COM_CORRETOR_DT"]
    - df_periodo.loc[mask_sla, "DATA_CAPTURA_DT"]
).dt.total_seconds() / 60.0
sla_medio_min = df_periodo["SLA_MIN"].mean()

# cálculo de data de referência para retorno (última interação ou com corretor)
df_periodo["DATA_REFERENCIA_RETORNO"] = df_periodo["DATA_ULT_INTERACAO_DT"]
mask_sem_ult = df_periodo["DATA_REFERENCIA_RETORNO"].isna() & df_periodo[
    "DATA_COM_CORRETOR_DT"
].notna()
df_periodo.loc[mask_sem_ult, "DATA_REFERENCIA_RETORNO"] = df_periodo.loc[
    mask_sem_ult, "DATA_COM_CORRETOR_DT"
]

hoje = pd.Timestamp(datetime.now().date())
df_periodo["DIAS_SEM_RETORNO"] = np.nan
mask_tem_ref = df_periodo["DATA_REFERENCIA_RETORNO"].notna()
df_periodo.loc[mask_tem_ref, "DIAS_SEM_RETORNO"] = (
    hoje - df_periodo.loc[mask_tem_ref, "DATA_REFERENCIA_RETORNO"].dt.normalize()
).dt.days

mask_sem_retorno_x = df_periodo["DIAS_SEM_RETORНО"] >= dias_sem_retorno
leads_sem_retorno_qtde = int(mask_sem_retorno_x.sum())

# ---------------------------------------------------------
# CARDS RESUMO
# ---------------------------------------------------------
st.markdown("## 🧾 Visão geral do atendimento")

c1, c2, c3, c4, c5 = st.columns(5)
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

if nome_busca.strip():
    df_match = df_periodo[
        df_periodo["NOME_LEAD"].str.contains(nome_busca.strip(), case=False, na=False)
    ].copy()

    if df_match.empty:
        st.info("Nenhum lead encontrado com esse nome dentro dos filtros.")
    else:
        # se vier mais de um, deixa escolher
        if len(df_match) > 1:
            df_match["OPCAO"] = (
                df_match["NOME_LEAD"].astype(str)
                + " | "
                + df_match["TELEFONE_LEAD"].astype(str)
                + " | "
                + df_match["CORRETOR_EXIBICAO"].astype(str)
            )
            opcao = st.selectbox(
                "Foram encontrados vários leads. Selecione:",
                df_match["OPCAO"].tolist(),
            )
            lead_sel = df_match[df_match["OPCAO"] == opcao].iloc[0]
        else:
            lead_sel = df_match.iloc[0]

        st.markdown("### 🔐 Detalhes do lead")

        c_a, c_b, c_c = st.columns(3)
        with c_a:
            st.metric("Lead", lead_sel["NOME_LEAD"])
            st.write(f"**Telefone:** {lead_sel['TELEFONE_LEAD']}")
        with c_b:
            st.write(f"**Corretor:** {lead_sel['CORRETOR_EXIBICAO']}")
            if col_origem:
                st.write(f"**Origem:** {lead_sel[col_origem]}")
            if col_campanha:
                st.write(f"**Campanha:** {lead_sel[col_campanha]}")
        with c_c:
            if col_situacao:
                st.write(f"**Situação:** {lead_sel[col_situacao]}")
            if col_etapa:
                st.write(f"**Etapa:** {lead_sel[col_etapa]}")

        c_d, c_e, c_f = st.columns(3)
        with c_d:
            st.write(f"**Capturado em:** {fmt_dt(lead_sel['DATA_CAPTURA_DT'])}")
        with c_e:
            st.write(f"**Com corretor em:** {fmt_dt(lead_sel['DATA_COM_CORRETOR_DT'])}")
        with c_f:
            st.write(f"**Última interação:** {fmt_dt(lead_sel['DATA_ULT_INTERACAO_DT'])}")

        c_g, c_h = st.columns(2)
        with c_g:
            st.write(f"**Data 'vendendo':** {fmt_dt(lead_sel['DATA_VENDENDO_DT'])}")
        with c_h:
            st.write(
                f"**Data vendido/perdido:** {fmt_dt(lead_sel['DATA_VENDIDO_PERDIDO_DT'])}"
            )

        # linha do tempo
        timeline = []
        timeline.append(f"- 📥 Lead capturado em **{fmt_dt(lead_sel['DATA_CAPTURA_DT'])}**.")
        if not pd.isna(lead_sel["DATA_COM_CORRETOR_DT"]):
            timeline.append(
                f"- 🤝 Encaminhado ao corretor **{lead_sel['CORRETOR_EXIBICAO']}** em **{fmt_dt(lead_sel['DATA_COM_CORRETOR_DT'])}**."
            )
        if not pd.isna(lead_sel["DATA_VENDENDO_DT"]):
            timeline.append(
                f"- 🧩 Marcado como **em atendimento/vendendo** em **{fmt_dt(lead_sel['DATA_VENDENDO_DT'])}**."
            )
        if not pd.isna(lead_sel["DATA_ULT_INTERACAO_DT"]):
            timeline.append(
                f"- 🗣️ Última interação registrada em **{fmt_dt(lead_sel['DATA_ULT_INTERACAO_DT'])}**."
            )
        if not pd.isna(lead_sel["DATA_VENDIDO_PERDIDO_DT"]):
            timeline.append(
                f"- ✅/❌ Marcado como **vendido/perdido** em **{fmt_dt(lead_sel['DATA_VENDIDO_PERDIDO_DT'])}**."
            )

        st.markdown("#### 📆 Linha do tempo de ações")
        if timeline:
            st.markdown("\n".join(timeline))
        else:
            st.write("Nenhuma ação registrada além da captura.")

        if col_descricao and pd.notna(lead_sel[col_descricao]):
            st.markdown("#### 📝 Observações / últimas informações")
            st.write(str(lead_sel[col_descricao]))

# ---------------------------------------------------------
# RANKING POR CORRETOR
# ---------------------------------------------------------
st.markdown("---")
st.markdown("## 👤 Ranking de atendimento por corretor")

df_rank = df_periodo.copy()
agrup = (
    df_rank.groupby("CORRETOR_EXIBICAO")
    .agg(
        LEADS=("NOME_LEAD", "count"),
        ATENDIDOS=("ATENDIDO", "sum"),
        SLA_MEDIO_MIN=("SLA_MIN", "mean"),
    )
    .reset_index()
)
agrup["NAO_ATENDIDOS"] = agrup["LEADS"] - agrup["ATENDIDOS"]
agrup["TAXA_ATENDIMENTO_%"] = np.where(
    agrup["LEADS"] > 0, agrup["ATENDIDOS"] / agrup["LEADS"] * 100, 0.0
)

agrup = agrup.sort_values(["LEADS", "ATENDIDOS"], ascending=[False, False])

df_rank_exibe = agrup.copy()
df_rank_exibe["SLA_MEDIO"] = df_rank_exibe["SLA_MEDIO_MIN"].apply(format_minutes)
df_rank_exibe["TAXA_ATENDIMENTO_%"] = df_rank_exibe["TAXA_ATENDIMENTO_%"].round(1)

df_rank_exibe = df_rank_exibe[
    [
        "CORRETOR_EXIBICAO",
        "LEADS",
        "ATENDIDOS",
        "NAO_ATENDIDOS",
        "TAXA_ATENDIMENTO_%",
        "SLA_MEDIO",
    ]
].rename(
    columns={
        "CORRETOR_EXIBICAO": "Corretor",
        "LEADS": "Leads",
        "ATENDIDOS": "Atendidos",
        "NAO_ATENDIDOS": "Não atendidos",
        "TAXA_ATENDIMENTO_%": "Atendimento (%)",
        "SLA_MEDIO": "SLA médio",
    }
)

st.dataframe(df_rank_exibe, use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# LEADS DO PERÍODO (DETALHADO)
# ---------------------------------------------------------
st.markdown("---")
st.markdown("## 📋 Leads do período (detalhado)")

df_det = df_periodo.copy()
colunas_det = [
    "NOME_LEAD",
    "TELEFONE_LEAD",
    "CORRETOR_EXIBICAO",
    "DATA_CAPTURA_DT",
    "DATA_REFERENCIA_RETORНО",
    "DIAS_SEM_RETORNO",
]
if col_situacao:
    colunas_det.append(col_situacao)
if col_etapa:
    colunas_det.append(col_etapa)
if col_descricao:
    colunas_det.append(col_descricao)

df_tab_det = df_det[colunas_det].copy()
df_tab_det = df_tab_det.rename(
    columns={
        "NOME_LEAD": "Lead",
        "TELEFONE_LEAD": "Telefone",
        "CORRETOR_EXIBICAO": "Corretor",
        "DATA_CAPTURA_DT": "Data captura",
        "DATA_REFERENCIA_RETORНО": "Último contato",
        "DIAS_SEM_RETORNO": "Dias sem retorno",
        col_situacao: "Situação" if col_situacao else col_situacao,
        col_etapa: "Etapa" if col_etapa else col_etapa,
        col_descricao: "Descrição" if col_descricao else col_descricao,
    }
)

# formata datas
for c in ["Data captura", "Último contato"]:
    if c in df_tab_det.columns:
        df_tab_det[c] = (
            pd.to_datetime(df_tab_det[c], errors="coerce").dt.strftime("%d/%m/%Y %H:%M")
        )

st.dataframe(df_tab_det, use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# LEADS SEM RETORNO HÁ X DIAS OU MAIS
# ---------------------------------------------------------
st.markdown("---")
st.markdown(f"## ⏰ Leads sem retorno há {dias_sem_retorno} dias ou mais")

df_sem_ret = df_periodo[mask_sem_retorno_x].copy()
if df_sem_ret.empty:
    st.info("Nenhum lead sem retorno no intervalo de dias selecionado.")
else:
    colunas_uc = [
        "NOME_LEAD",
        "TELEFONE_LEAD",
        "CORRETOR_EXIBICAO",
        "DATA_REFERENCIA_RETORНО",
        "DIAS_SEM_RETORNO",
    ]
    if col_situacao:
        colunas_uc.append(col_situacao)
    if col_etapa:
        colunas_uc.append(col_etapa)

    df_tab_uc = df_sem_ret[colunas_uc].copy()
    df_tab_uc = df_tab_uc.rename(
        columns={
            "NOME_LEAD": "Lead",
            "TELEFONE_LEAD": "Telefone",
            "CORRETOR_EXIBICAO": "Corretor",
            "DATA_REFERENCIA_RETORНО": "Último contato",
            "DIAS_SEM_RETORНО": "Dias sem retorno",
            col_situacao: "Situação" if col_situacao else col_situacao,
            col_etapa: "Etapa" if col_etapa else col_etapa,
        }
    )
    df_tab_uc["Último contato"] = pd.to_datetime(
        df_tab_uc["Último contato"], errors="coerce"
    ).dt.strftime("%d/%m/%Y %H:%M")
    st.dataframe(df_tab_uc, use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# LEADS COM APENAS 1 CONTATO
# ---------------------------------------------------------
st.markdown("---")
st.markdown("## ☎️ Leads com apenas 1 contato")

# vamos considerar contato = registro de DATA_REFERENCIA_RETORNO
# se quisermos ser mais sofisticados no futuro, podemos usar o histórico
# de interações via outra API.
df_1c = df_periodo.copy()

# se não tem DATA_COM_CORRETOR_DT -> 0 contatos
# se tem DATA_COM_CORRETOR_DT mas não tem DATA_ULT_INTERACAO_DT -> 1 contato
# se tem ambas -> 2 ou mais (não distinguimos mais do que isso)
cond_sem_atendimento = df_1c["DATA_COM_CORRETOR_DT"].isna()
cond_um_contato = df_1c["DATA_COM_CORRETOR_DT"].notna() & df_1c[
    "DATA_ULT_INTERACAO_DT"
].isna()

df_1contato = df_1c[cond_um_contato].copy()

if df_1contato.empty:
    st.info("Não há leads com apenas 1 contato neste período.")
else:
    colunas_1c = [
        "NOME_LEAD",
        "TELEFONE_LEAD",
        "CORRETOR_EXIBICAO",
        "DATA_COM_CORRETOR_DT",
    ]
    if col_situacao:
        colunas_1c.append(col_situacao)
    if col_etapa:
        colunas_1c.append(col_etapa)

    df_tab_1c = df_1contato[colunas_1c].copy()
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
