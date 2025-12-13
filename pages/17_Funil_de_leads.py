# =========================================================
# FUNIL DE LEADS – ORIGEM, STATUS E CONVERSÃO (COM FILTROS)
# Período (DIA / DATA BASE) + Equipe + Corretor + Origem
# =========================================================

import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date

from utils.supremo_config import TOKEN_SUPREMO

st.set_page_config(page_title="Funil de Leads", page_icon="📊", layout="wide")
st.title("📊 Funil de Leads – Origem, Status e Conversão")

# =========================================================
# PLANILHA (MANTENDO A MESMA FONTE)
# =========================================================
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

# =========================================================
# FUNÇÕES
# =========================================================
MESES = {
    "JANEIRO": 1, "FEVEREIRO": 2, "MARÇO": 3, "MARCO": 3,
    "ABRIL": 4, "MAIO": 5, "JUNHO": 6, "JULHO": 7,
    "AGOSTO": 8, "SETEMBRO": 9, "OUTUBRO": 10,
    "NOVEMBRO": 11, "DEZEMBRO": 12,
}

def parse_data(col):
    return pd.to_datetime(col, dayfirst=True, errors="coerce")

def parse_data_base_label(label: str):
    """
    label tipo: 'novembro 2025' -> date(2025, 11, 1)
    """
    if label is None:
        return pd.NaT
    s = str(label).strip().upper()
    parts = s.split()
    if len(parts) < 2:
        return pd.NaT
    mes = MESES.get(parts[0])
    try:
        ano = int(parts[-1])
    except:
        return pd.NaT
    if not mes:
        return pd.NaT
    return date(ano, mes, 1)

@st.cache_data(ttl=300)
def carregar_planilha():
    df = pd.read_csv(CSV_URL, dtype=str)
    df.columns = df.columns.str.upper().str.strip()

    # campos base
    df["DATA"] = parse_data(df["DATA"])
    df = df.dropna(subset=["DATA"])

    df["DATA_BASE_LABEL"] = df.get("DATA BASE", "").astype(str).str.strip()
    df["DATA_BASE_DATE"] = df["DATA_BASE_LABEL"].apply(parse_data_base_label)

    df["CLIENTE"] = df["CLIENTE"].astype(str).str.upper().str.strip()
    df["CORRETOR"] = df["CORRETOR"].astype(str).str.upper().str.strip()
    df["EQUIPE"] = df["EQUIPE"].astype(str).str.upper().str.strip()
    df["STATUS_RAW"] = df["SITUAÇÃO"].astype(str).str.upper().str.strip()

    # mapeamento status
    df["STATUS_BASE"] = ""
    df.loc[df["STATUS_RAW"].str.contains("EM ANÁLISE"), "STATUS_BASE"] = "ANALISE"
    df.loc[df["STATUS_RAW"].str.contains("REANÁLISE"), "STATUS_BASE"] = "REANALISE"
    df.loc[df["STATUS_RAW"].str.contains("APROVADO BACEN"), "STATUS_BASE"] = "APROVADO_BACEN"
    df.loc[df["STATUS_RAW"].str.contains("APROVA"), "STATUS_BASE"] = "APROVADO"
    df.loc[df["STATUS_RAW"].str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
    df.loc[df["STATUS_RAW"].str.contains("PEND"), "STATUS_BASE"] = "PENDENCIA"
    df.loc[df["STATUS_RAW"].str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA_GERADA"
    df.loc[df["STATUS_RAW"].str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA_INFORMADA"
    df.loc[df["STATUS_RAW"].str.contains("DESIST"), "STATUS_BASE"] = "DESISTIU"

    # garante que só pega linhas válidas do funil
    df = df[df["STATUS_BASE"] != ""]

    # ÚLTIMO STATUS POR CLIENTE (lead não sai do funil)
    df = df.sort_values("DATA")
    df = df.groupby("CLIENTE", as_index=False).last()

    return df

@st.cache_data(ttl=1800)
def carregar_crm_ultimos_1000():
    url = "https://api.supremocrm.com.br/v1/leads"
    headers = {"Authorization": f"Bearer {TOKEN_SUPREMO}"}

    dados, pagina = [], 1
    while len(dados) < 1000:
        r = requests.get(url, headers=headers, params={"pagina": pagina}, timeout=20)
        if r.status_code != 200:
            break
        js = r.json()
        if not js.get("data"):
            break
        dados.extend(js["data"])
        pagina += 1

    df = pd.DataFrame(dados)
    if df.empty:
        return pd.DataFrame(columns=["CLIENTE", "ORIGEM", "CAMPANHA"])

    df["CLIENTE"] = df["nome_pessoa"].astype(str).str.upper().str.strip()
    df["ORIGEM"] = df.get("nome_origem", "SEM CADASTRO NO CRM").fillna("SEM CADASTRO NO CRM")
    df["CAMPANHA"] = df.get("nome_campanha", "-").fillna("-")

    df["ORIGEM"] = df["ORIGEM"].astype(str).str.upper().str.strip()
    df["CAMPANHA"] = df["CAMPANHA"].astype(str).str.upper().str.strip()

    return df[["CLIENTE", "ORIGEM", "CAMPANHA"]]

# =========================================================
# CARGA
# =========================================================
df_plan = carregar_planilha()
df_crm = carregar_crm_ultimos_1000()

df = df_plan.merge(df_crm, on="CLIENTE", how="left")
df["ORIGEM"] = df["ORIGEM"].fillna("SEM CADASTRO NO CRM").astype(str).str.upper().str.strip()
df["CAMPANHA"] = df["CAMPANHA"].fillna("-").astype(str).str.upper().str.strip()

# =========================================================
# SIDEBAR – FILTROS
# =========================================================
st.sidebar.header("Filtros")

modo_periodo = st.sidebar.radio("Modo de período", ["DIA", "DATA BASE"])

df_filtrado = df.copy()

if modo_periodo == "DIA":
    min_d = df_filtrado["DATA"].min().date()
    max_d = df_filtrado["DATA"].max().date()

    ini, fim = st.sidebar.date_input(
        "Período (DIA)",
        value=(min_d, max_d)
    )
    df_filtrado = df_filtrado[
        (df_filtrado["DATA"].dt.date >= ini) &
        (df_filtrado["DATA"].dt.date <= fim)
    ]
else:
    bases = df_filtrado["DATA_BASE_LABEL"].dropna().unique().tolist()
    bases = sorted(bases, key=lambda x: (parse_data_base_label(x) or date(1900,1,1)))
    bases_sel = st.sidebar.multiselect(
        "Data Base",
        options=bases,
        default=bases
    )
    if bases_sel:
        df_filtrado = df_filtrado[df_filtrado["DATA_BASE_LABEL"].isin(bases_sel)]

# Equipe
equipes = sorted([e for e in df_filtrado["EQUIPE"].dropna().unique().tolist() if e.strip() != ""])
equipe_sel = st.sidebar.selectbox("Equipe", ["TODAS"] + equipes)
if equipe_sel != "TODAS":
    df_filtrado = df_filtrado[df_filtrado["EQUIPE"] == equipe_sel]

# Corretor
corretores = sorted([c for c in df_filtrado["CORRETOR"].dropna().unique().tolist() if c.strip() != ""])
corretor_sel = st.sidebar.selectbox("Corretor", ["TODOS"] + corretores)
if corretor_sel != "TODOS":
    df_filtrado = df_filtrado[df_filtrado["CORRETOR"] == corretor_sel]

# =========================================================
# STATUS ATUAL (MACRO DO PERÍODO SELECIONADO)
# =========================================================
st.subheader("📌 Status Atual do Funil (período selecionado)")

kpi = df_filtrado["STATUS_BASE"].value_counts()

# REGRA: DESISTIU anula apenas as vendas (não some do funil)
vendas_validas = df_filtrado[
    (df_filtrado["STATUS_BASE"].isin(["VENDA_GERADA", "VENDA_INFORMADA"])) &
    (df_filtrado["STATUS_BASE"] != "DESISTIU")
]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Em Análise", int(kpi.get("ANALISE", 0)))
c2.metric("Reanálise", int(kpi.get("REANALISE", 0)))
c3.metric("Pendência", int(kpi.get("PENDENCIA", 0)))
c4.metric("Reprovado", int(kpi.get("REPROVADO", 0)))

c5, c6, c7, c8 = st.columns(4)
c5.metric("Aprovado", int(kpi.get("APROVADO", 0)))
c6.metric("Aprovado Bacen", int(kpi.get("APROVADO_BACEN", 0)))
c7.metric("Desistiu", int(kpi.get("DESISTIU", 0)))
c8.metric("Leads no Funil", int(len(df_filtrado)))

c9, c10 = st.columns(2)
c9.metric("Vendas Informadas", int((df_filtrado["STATUS_BASE"] == "VENDA_INFORMADA").sum() - 0))
c10.metric("Vendas Geradas", int((df_filtrado["STATUS_BASE"] == "VENDA_GERADA").sum() - 0))

# =========================================================
# PERFORMANCE E CONVERSÃO POR ORIGEM + TABELA
# =========================================================
st.subheader("📈 Performance e Conversão por Origem")

origens = ["TODAS"] + sorted(df_filtrado["ORIGEM"].dropna().unique().tolist())
origem_sel = st.selectbox("Origem", origens)

df_o = df_filtrado if origem_sel == "TODAS" else df_filtrado[df_filtrado["ORIGEM"] == origem_sel]

# Base de conversão (estoque do funil, sem remover lead ao vender)
leads = len(df_o)

# para conversão “Lead -> Análise”, considera que qualquer status a partir de análise conta como análise no funil
analises = df_o[df_o["STATUS_BASE"].isin([
    "ANALISE", "REANALISE", "APROVADO", "APROVADO_BACEN", "VENDA_GERADA", "VENDA_INFORMADA", "REPROVADO", "PENDENCIA"
])].shape[0]

# “Aprovados” considera aprovado/aprovado bacen e também quem já vendeu (porque passou por aprovação)
aprovados = df_o[df_o["STATUS_BASE"].isin([
    "APROVADO", "APROVADO_BACEN", "VENDA_GERADA", "VENDA_INFORMADA"
])].shape[0]

# Vendas (DESISTIU não apaga lead, mas anula venda – então desistido nunca entra como venda)
vendas = df_o[df_o["STATUS_BASE"].isin(["VENDA_GERADA", "VENDA_INFORMADA"])].shape[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Leads", int(leads))
c2.metric("Análises (funil)", int(analises))
c3.metric("Aprovados (funil)", int(aprovados))
c4.metric("Vendas (funil)", int(vendas))

c5, c6, c7, c8 = st.columns(4)
c5.metric("Lead → Análise", f"{(analises/leads*100 if leads else 0):.1f}%")
c6.metric("Análise → Aprovação", f"{(aprovados/analises*100 if analises else 0):.1f}%")
c7.metric("Análise → Venda", f"{(vendas/analises*100 if analises else 0):.1f}%")
c8.metric("Aprovação → Venda", f"{(vendas/aprovados*100 if aprovados else 0):.1f}%")

# =========================================================
# TABELA DE LEADS DA ORIGEM
# =========================================================
st.divider()
st.subheader("📋 Leads da Origem Selecionada")

tabela = df_o[["CLIENTE", "CORRETOR", "EQUIPE", "STATUS_BASE", "DATA"]].copy()
tabela = tabela.sort_values("DATA", ascending=False)
tabela.rename(columns={"DATA": "ULTIMA_ATUALIZACAO"}, inplace=True)

st.dataframe(tabela, use_container_width=True)
