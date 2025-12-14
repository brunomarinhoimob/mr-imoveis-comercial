# =========================================================
# FUNIL DE LEADS – MR IMÓVEIS (VERSÃO FINAL OFICIAL)
# =========================================================

import streamlit as st
import pandas as pd
import numpy as np
import requests
import unicodedata
import re
from datetime import date

# =========================
# CONFIGURAÇÕES GERAIS
# =========================
st.set_page_config(
    page_title="Funil de Leads | MR Imóveis",
    layout="wide"
)

LOGO_PATH = "logo_mr.png"

SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID = "1574157905"
URL_PLANILHA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

URL_CRM = "https://app.crm.supremo.app/api/leads"
TOKEN_SUPREMO = st.secrets.get("TOKEN_SUPREMO", None)

CACHE_TTL = 60 * 30  # 30 minutos

# =========================
# FUNÇÕES AUXILIARES
# =========================
def normalizar(txt):
    if pd.isna(txt):
        return ""
    txt = str(txt)
    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    txt = re.sub(r"[^A-Za-z0-9 ]+", " ", txt)
    return re.sub(r"\s+", " ", txt).strip().upper()

def pct(a, b):
    return f"{(a / b * 100):.1f}%" if b > 0 else "0%"

# =========================
# CARREGAMENTO PLANILHA
# =========================
@st.cache_data(ttl=CACHE_TTL)
def carregar_planilha():
    df = pd.read_csv(URL_PLANILHA, dtype=str)
    df.columns = [c.upper().strip() for c in df.columns]

    df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce", dayfirst=True)
    df = df.dropna(subset=["DATA"])

    for col in ["CLIENTE", "CORRETOR", "EQUIPE", "SITUACAO", "DATA BASE"]:
        if col not in df.columns:
            df[col] = ""

    df["CLIENTE"] = df["CLIENTE"].map(normalizar)
    df["CORRETOR"] = df["CORRETOR"].map(normalizar)
    df["EQUIPE"] = df["EQUIPE"].map(normalizar)
    df["DATA_BASE"] = df["DATA BASE"].astype(str)

    df["STATUS_BASE"] = df["SITUACAO"].map(normalizar)

    df["LEAD_KEY"] = df["CLIENTE"]

    return df

# =========================
# CARREGAMENTO CRM (SEGURO)
# =========================
@st.cache_data(ttl=CACHE_TTL)
def carregar_crm():
    cols = ["LEAD_KEY", "ORIGEM", "CAMPANHA"]

    if not TOKEN_SUPREMO:
        return pd.DataFrame(columns=cols)

    try:
        headers = {"Authorization": f"Bearer {TOKEN_SUPREMO}"}
        r = requests.get(URL_CRM, headers=headers, timeout=20)
        r.raise_for_status()
        dados = r.json().get("dados", [])

        df = pd.DataFrame(dados)
        if df.empty:
            return pd.DataFrame(columns=cols)

        df["LEAD_KEY"] = df["nome_pessoa"].map(normalizar)
        df["ORIGEM"] = df["nome_origem"].fillna("SEM ORIGEM").map(normalizar)
        df["CAMPANHA"] = df["nome_campanha"].fillna("SEM CAMPANHA").map(normalizar)

        return df[cols].drop_duplicates("LEAD_KEY", keep="last")

    except Exception:
        st.warning("⚠️ CRM indisponível. Origem exibida como SEM CADASTRO NO CRM.")
        return pd.DataFrame(columns=cols)

# =========================
# CARGA GERAL
# =========================
df_plan = carregar_planilha()
df_crm = carregar_crm()

df = df_plan.merge(df_crm, on="LEAD_KEY", how="left")
df["ORIGEM"] = df["ORIGEM"].fillna("SEM CADASTRO NO CRM")
df["CAMPANHA"] = df["CAMPANHA"].fillna("SEM CAMPANHA")

# =========================
# ÚLTIMA MOVIMENTAÇÃO
# =========================
df_ult = (
    df.sort_values("DATA")
      .groupby("LEAD_KEY", as_index=False)
      .last()
)

# =========================
# HEADER
# =========================
col_logo, col_title = st.columns([1, 6])
with col_logo:
    st.image(LOGO_PATH, width=130)
with col_title:
    st.title("🎯 Funil de Leads – Gestão, Origem e Conversão")

# =========================
# STATUS ATUAL
# =========================
st.subheader("📌 Status Atual do Funil")

def cnt(status):
    return (df_ult["STATUS_BASE"] == status).sum()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Em Análise", cnt("EM ANALISE"))
c2.metric("Reanálises", cnt("REANALISE"))
c3.metric("Reprovados", cnt("REPROVADO"))
c4.metric("Aprovados", cnt("APROVADO"))
c5.metric("Vendas Geradas", cnt("VENDA GERADA"))

# =========================
# PERFORMANCE POR ORIGEM
# =========================
st.markdown("---")
st.subheader("📈 Performance e Conversão por Origem")

origem_sel = st.selectbox(
    "Origem",
    ["TODAS"] + sorted(df_ult["ORIGEM"].unique())
)

df_o = df_ult if origem_sel == "TODAS" else df_ult[df_ult["ORIGEM"] == origem_sel]

leads = len(df_o)
analises = (df_o["STATUS_BASE"] == "EM ANALISE").sum()
reanalises = (df_o["STATUS_BASE"] == "REANALISE").sum()
aprovados = df_o["STATUS_BASE"].str.contains("APROVADO", na=False).sum()
vendas = (df_o["STATUS_BASE"] == "VENDA GERADA").sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Leads", leads)
c2.metric("Análises", analises)
c3.metric("Reanálises", reanalises)
c4.metric("Vendas", vendas)

c1.metric("Lead → Análise", pct(analises, leads))
c2.metric("Análise → Aprovação", pct(aprovados, analises))
c3.metric("Análise → Venda", pct(vendas, analises))
c4.metric("Aprovação → Venda", pct(vendas, aprovados))

# =========================
# RANKING ORIGEM POR VGV
# =========================
st.markdown("---")
st.subheader("🏆 Ranking de Origem por VGV")

if "VGV" in df.columns:
    ranking_vgv = (
        df[df["STATUS_BASE"] == "VENDA GERADA"]
        .groupby("ORIGEM")["VGV"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    st.dataframe(ranking_vgv, use_container_width=True)
else:
    st.info("Coluna VGV não encontrada na planilha.")

# =========================
# ORIGEM × CORRETOR
# =========================
st.markdown("---")
st.subheader("🔀 Origem × Corretor")

origem_corretor = (
    df_ult.groupby(["ORIGEM", "CORRETOR"])
    .agg(
        Leads=("LEAD_KEY", "count"),
        Analises=("STATUS_BASE", lambda x: (x == "EM ANALISE").sum()),
        Vendas=("STATUS_BASE", lambda x: (x == "VENDA GERADA").sum())
    )
    .reset_index()
)

st.dataframe(origem_corretor, use_container_width=True)

# =========================
# ORIGEM × CAMPANHA
# =========================
st.markdown("---")
st.subheader("🎯 Origem × Campanha")

origem_campanha = (
    df_ult.groupby(["ORIGEM", "CAMPANHA"])
    .agg(
        Leads=("LEAD_KEY", "count"),
        Analises=("STATUS_BASE", lambda x: (x == "EM ANALISE").sum()),
        Vendas=("STATUS_BASE", lambda x: (x == "VENDA GERADA").sum())
    )
    .reset_index()
)

st.dataframe(origem_campanha, use_container_width=True)

# =========================
# ALERTAS AUTOMÁTICOS
# =========================
st.markdown("---")
st.subheader("🚨 Alertas Automáticos")

for _, row in origem_corretor.iterrows():
    if row["Leads"] >= 10:
        conv = row["Vendas"] / max(row["Leads"], 1)
        if conv < 0.05:
            st.warning(
                f"⚠️ Conversão baixa ({conv:.1%}) | "
                f"Origem: {row['ORIGEM']} | Corretor: {row['CORRETOR']}"
            )

# =========================
# AUDITORIA DE LEAD
# =========================
st.markdown("---")
st.subheader("🔎 Auditoria de Lead")

busca = st.text_input("Buscar cliente pelo nome")

if busca:
    chave = normalizar(busca)
    hist = df[df["LEAD_KEY"].str.contains(chave, na=False)]

    if hist.empty:
        st.warning("Lead não encontrado.")
    else:
        atual = hist.sort_values("DATA").iloc[-1]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Situação Atual", atual["STATUS_BASE"])
        c2.metric("Corretor", atual["CORRETOR"])
        c3.metric("Equipe", atual["EQUIPE"])
        c4.metric("Origem", atual["ORIGEM"])

        st.markdown("### 🕒 Linha do Tempo")
        st.dataframe(
            hist.sort_values("DATA")[["DATA", "STATUS_BASE"]],
            use_container_width=True
        )
