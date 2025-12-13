import streamlit as st
import pandas as pd
from datetime import date

from app_dashboard import carregar_dados_planilha

st.set_page_config(
    page_title="Funil de Leads",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Funil de Leads – Origem, Status e Conversão")

# =====================================================
# FUNÇÕES AUXILIARES
# =====================================================

def normalizar_nome(nome):
    if pd.isna(nome):
        return ""
    return " ".join(str(nome).upper().split())


def calcular_taxa(a, b):
    return f"{(a / b * 100):.1f}%" if b else "0%"


# =====================================================
# CARGA DE DADOS (MESMA BASE DO CLIENTES MR)
# =====================================================
@st.cache_data(ttl=1800)
def carregar_dados_funil():
    df = carregar_dados_planilha()
    df.columns = [c.upper().strip() for c in df.columns]

    # DIA
    if "DIA" in df.columns:
        df["DIA"] = pd.to_datetime(df["DIA"], errors="coerce")
    elif "DATA" in df.columns:
        df["DIA"] = pd.to_datetime(df["DATA"], errors="coerce")
    else:
        df["DIA"] = pd.NaT

    df = df.dropna(subset=["DIA"])

    # NOME CLIENTE
    col_nome = next(
        (c for c in ["CLIENTE", "NOME", "NOME CLIENTE", "NOME DO CLIENTE"] if c in df.columns),
        None,
    )
    if col_nome:
        df["NOME_CLIENTE"] = df[col_nome].apply(normalizar_nome)
    else:
        df["NOME_CLIENTE"] = "NÃO INFORMADO"

    # STATUS
    col_status = next(
        (c for c in ["SITUAÇÃO", "SITUACAO", "STATUS", "SITUAÇÃO ATUAL"] if c in df.columns),
        None,
    )
    if col_status:
        df["STATUS_BASE"] = (
            df[col_status]
            .fillna("")
            .astype(str)
            .str.upper()
            .str.strip()
        )
    else:
        df["STATUS_BASE"] = ""

    # CORRETOR / EQUIPE
    df["CORRETOR"] = (
        df["CORRETOR"] if "CORRETOR" in df.columns else "NÃO INFORMADO"
    )
    df["CORRETOR"] = df["CORRETOR"].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()

    df["EQUIPE"] = (
        df["EQUIPE"] if "EQUIPE" in df.columns else "NÃO INFORMADO"
    )
    df["EQUIPE"] = df["EQUIPE"].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()

    # 🔥 CORREÇÃO DO ERRO (ORIGEM)
    if "ORIGEM" not in df.columns:
        df["ORIGEM"] = "SEM CADASTRO NO CRM"
    else:
        df["ORIGEM"] = (
            df["ORIGEM"]
            .fillna("SEM CADASTRO NO CRM")
            .astype(str)
            .str.upper()
            .str.strip()
        )

    return df


df = carregar_dados_funil()

# =====================================================
# FILTROS
# =====================================================
st.subheader("🎛️ Filtros")

c1, c2, c3 = st.columns(3)

with c1:
    data_inicio, data_fim = st.date_input(
        "Período",
        value=(df["DIA"].min().date(), df["DIA"].max().date()),
        min_value=df["DIA"].min().date(),
        max_value=df["DIA"].max().date(),
    )

with c2:
    equipes = ["TODAS"] + sorted(df["EQUIPE"].unique())
    equipe_sel = st.selectbox("Equipe", equipes)

with c3:
    corretores = ["TODOS"] + sorted(df["CORRETOR"].unique())
    corretor_sel = st.selectbox("Corretor", corretores)

df_f = df[
    (df["DIA"].dt.date >= data_inicio) &
    (df["DIA"].dt.date <= data_fim)
]

if equipe_sel != "TODAS":
    df_f = df_f[df_f["EQUIPE"] == equipe_sel]

if corretor_sel != "TODOS":
    df_f = df_f[df_f["CORRETOR"] == corretor_sel]

# =====================================================
# ÚLTIMO STATUS POR CLIENTE
# =====================================================
df_f = df_f.sort_values("DIA")
df_f = df_f.groupby("NOME_CLIENTE", as_index=False).last()

# =====================================================
# KPIs MACRO
# =====================================================
st.markdown("## 📌 Status Atual do Funil")

col1, col2, col3, col4 = st.columns(4)

def kpi(col, label, value):
    col.metric(label, int(value))

kpi(col1, "Em Análise", (df_f["STATUS_BASE"] == "EM ANÁLISE").sum())
kpi(col1, "Reanálise", (df_f["STATUS_BASE"] == "REANÁLISE").sum())

kpi(col2, "Aprovados", (df_f["STATUS_BASE"] == "APROVAÇÃO").sum())
kpi(col2, "Aprovados Bacen", (df_f["STATUS_BASE"] == "APROVADO BACEN").sum())

kpi(col3, "Pendências", (df_f["STATUS_BASE"] == "PENDÊNCIA").sum())
kpi(col3, "Reprovados", (df_f["STATUS_BASE"] == "REPROVAÇÃO").sum())

kpi(col4, "Vendas Geradas", (df_f["STATUS_BASE"] == "VENDA GERADA").sum())
kpi(col4, "Vendas Informadas", (df_f["STATUS_BASE"] == "VENDA INFORMADA").sum())

st.metric(
    "Leads Ativos no Funil",
    df_f[~df_f["STATUS_BASE"].isin(["DESISTIU", "VENDA GERADA"])].shape[0],
)

# =====================================================
# PERFORMANCE POR ORIGEM + CONVERSÃO
# =====================================================
st.divider()
st.markdown("## 📍 Performance e Conversão por Origem")

origens = ["TODAS"] + sorted(df_f["ORIGEM"].unique())
origem_sel = st.selectbox("Origem", origens)

df_o = df_f if origem_sel == "TODAS" else df_f[df_f["ORIGEM"] == origem_sel]

leads = len(df_o)
analises = (df_o["STATUS_BASE"] == "EM ANÁLISE").sum()
aprov = df_o["STATUS_BASE"].isin(["APROVAÇÃO", "APROVADO BACEN"]).sum()
vendas = df_o["STATUS_BASE"].isin(["VENDA GERADA", "VENDA INFORMADA"]).sum()

cA, cB, cC, cD = st.columns(4)

cA.metric("Leads", leads)
cB.metric("Análises", analises)
cC.metric("Aprovados", aprov)
cD.metric("Vendas", vendas)

c1, c2, c3, c4 = st.columns(4)

c1.metric("Lead → Análise", calcular_taxa(analises, leads))
c2.metric("Análise → Aprovação", calcular_taxa(aprov, analises))
c3.metric("Análise → Venda", calcular_taxa(vendas, analises))
c4.metric("Aprovação → Venda", calcular_taxa(vendas, aprov))

# =====================================================
# BUSCA DE CLIENTE
# =====================================================
st.divider()
st.markdown("## 🔎 Auditoria Rápida de Cliente")

busca = st.text_input("Digite o nome do cliente")

if busca.strip():
    nome = normalizar_nome(busca)
    df_cli = df[df["NOME_CLIENTE"].str.contains(nome, na=False)]

    if df_cli.empty:
        st.warning("Cliente não encontrado.")
    else:
        st.dataframe(
            df_cli.sort_values("DIA"),
            use_container_width=True,
            hide_index=True,
        )
else:
    st.info("Digite o nome acima para consultar um cliente.")
