# pages/17_Funil_de_leads.py
# -*- coding: utf-8 -*-

import re
import unicodedata
from datetime import date

import numpy as np
import pandas as pd
import requests
import streamlit as st

# =========================
# CONFIG
# =========================
# (usando o mesmo padrão do seu arquivo-base)
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID = "1574157905"
URL_PLANILHA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

try:
    from supremo_config import TOKEN_SUPREMO
except Exception:
    TOKEN_SUPREMO = ""

URL_CRM_ULTIMOS_1000 = "https://app.crm.supremo.app/api/leads?limit=1000"
TTL_CACHE = 60 * 30  # 30 min

# =========================
# UI
# =========================
st.set_page_config(page_title="Funil de Leads", layout="wide")

try:
    st.image("logo_mr.png", width=140)
except Exception:
    pass

st.title("🎯 Funil de Leads – Origem, Status e Conversão")

# =========================
# Helpers
# =========================
def _serie(df: pd.DataFrame, col: str, default: str = "") -> pd.Series:
    if col in df.columns:
        return df[col]
    return pd.Series([default] * len(df), index=df.index)

def normalizar_texto(x: str) -> str:
    if x is None:
        return ""
    x = str(x)
    x = unicodedata.normalize("NFKD", x)
    x = "".join([c for c in x if not unicodedata.combining(c)])
    x = re.sub(r"[^A-Za-z0-9]+", " ", x).strip().upper()
    x = re.sub(r"\s+", " ", x)
    return x

def to_date_safe(x):
    if pd.isna(x) or str(x).strip() == "":
        return pd.NaT
    return pd.to_datetime(x, errors="coerce", dayfirst=True)

STATUS_MAP = {
    "ANALISE": "EM ANÁLISE",
    "EM ANALISE": "EM ANÁLISE",
    "EM ANÁLISE": "EM ANÁLISE",
    "APROVACAO": "APROVAÇÃO",
    "APROVAÇÃO": "APROVAÇÃO",
    "APROVADO": "APROVAÇÃO",
    "REPROVACAO": "REPROVAÇÃO",
    "REPROVAÇÃO": "REPROVAÇÃO",
    "VENDA GERADA": "VENDA GERADA",
    "VENDA_GERADA": "VENDA GERADA",
    "VENDA INFORMADA": "VENDA INFORMADA",
    "VENDA_INFORMADA": "VENDA INFORMADA",
    "REANALISE": "REANÁLISE",
    "REANÁLISE": "REANÁLISE",
    "APROVADO BACEN": "APROVADO BACEN",
    "APROVACAO BACEN": "APROVADO BACEN",
    "APROVAÇÃO BACEN": "APROVADO BACEN",
    "DESISTIU": "DESISTIU",
    "PENDENCIA": "PENDÊNCIA",
    "PENDÊNCIA": "PENDÊNCIA",
}

def normalizar_status(x: str) -> str:
    x0 = normalizar_texto(x).replace("_", " ").strip()
    return STATUS_MAP.get(x0, x0 if x0 else "SEM STATUS")

def pct(a: float, b: float) -> float:
    if b == 0:
        return 0.0
    return round((a / b) * 100, 1)

# =========================
# LOADERS (cache)
# =========================
@st.cache_data(ttl=TTL_CACHE, show_spinner=True)
def carregar_planilha() -> pd.DataFrame:
    df = pd.read_csv(URL_PLANILHA, dtype=str)
    df.columns = [c.strip().upper() for c in df.columns]

    if "DATA" in df.columns and "DIA" not in df.columns:
        df["DIA"] = df["DATA"]
    if "DIA" not in df.columns:
        cand = [c for c in df.columns if "DATA" in c]
        if cand:
            df["DIA"] = df[cand[0]]
        else:
            df["DIA"] = ""

    df["DIA"] = df["DIA"].apply(to_date_safe)

    df["CLIENTE"] = _serie(df, "CLIENTE", _serie(df, "NOME", "")).fillna("").astype(str).str.strip().str.upper()
    df["CPF"] = _serie(df, "CPF", "").fillna("").astype(str).str.strip()
    df["EQUIPE"] = _serie(df, "EQUIPE", "").fillna("").astype(str).str.strip().str.upper()
    df["CORRETOR"] = _serie(df, "CORRETOR", "").fillna("").astype(str).str.strip().str.upper()

    if "DATA BASE" in df.columns and "DATA_BASE" not in df.columns:
        df["DATA_BASE"] = df["DATA BASE"]
    df["DATA_BASE"] = _serie(df, "DATA_BASE", "").fillna("").astype(str).str.strip().str.lower()

    if "SITUAÇÃO" in df.columns and "SITUACAO" not in df.columns:
        df["SITUACAO"] = df["SITUAÇÃO"]
    df["STATUS_BASE"] = _serie(df, "STATUS_BASE", _serie(df, "SITUACAO", "")).fillna("").map(normalizar_status)

    df["OBS"] = _serie(df, "OBSERVAÇÕES", _serie(df, "OBSERVACOES", "")).fillna("").astype(str)
    df["OBS2"] = _serie(df, "OBSERVAÇÕES 2", _serie(df, "OBSERVACOES2", _serie(df, "OBSERVACOES_2", ""))).fillna("").astype(str)

    df["CLIENTE_NORM"] = df["CLIENTE"].map(normalizar_texto)
    df["CPF_NORM"] = df["CPF"].astype(str).str.replace(r"\D+", "", regex=True)

    df = df[df["CLIENTE_NORM"].str.len() > 0].copy()
    df["LEAD_KEY"] = np.where(df["CPF_NORM"].str.len() >= 8, df["CPF_NORM"], df["CLIENTE_NORM"])
    return df

@st.cache_data(ttl=TTL_CACHE, show_spinner=True)
def carregar_crm_ultimos_1000() -> pd.DataFrame:
    if not TOKEN_SUPREMO:
        return pd.DataFrame(columns=["NOME_NORM", "ORIGEM_CRM", "CAMPANHA_CRM", "DATA_CAPTURA"])

    headers = {"Authorization": f"Bearer {TOKEN_SUPREMO}"}
    r = requests.get(URL_CRM_ULTIMOS_1000, headers=headers, timeout=30)
    r.raise_for_status()
    payload = r.json()

    dados = payload.get("dados", payload if isinstance(payload, list) else [])
    df = pd.DataFrame(dados)

    df["NOME"] = _serie(df, "nome_pessoa", "").fillna("").astype(str).str.strip().str.upper()
    df["NOME_NORM"] = df["NOME"].map(normalizar_texto)

    df["ORIGEM_CRM"] = _serie(df, "nome_origem", "SEM ORIGEM").fillna("SEM ORIGEM").astype(str).str.strip().str.upper()
    df["CAMPANHA_CRM"] = _serie(df, "nome_campanha", "SEM CAMPANHA").fillna("SEM CAMPANHA").astype(str).str.strip().str.upper()
    df["DATA_CAPTURA"] = _serie(df, "data_captura", "").apply(to_date_safe)

    df = df.sort_values("DATA_CAPTURA").drop_duplicates("NOME_NORM", keep="last")
    return df[["NOME_NORM", "ORIGEM_CRM", "CAMPANHA_CRM", "DATA_CAPTURA"]].copy()

def aplicar_origem_crm(df_plan: pd.DataFrame, df_crm: pd.DataFrame) -> pd.DataFrame:
    df = df_plan.merge(df_crm, left_on="CLIENTE_NORM", right_on="NOME_NORM", how="left")
    df["ORIGEM"] = df["ORIGEM_CRM"].fillna("SEM CADASTRO NO CRM").astype(str).str.strip().str.upper()
    df["CAMPANHA"] = df["CAMPANHA_CRM"].fillna("SEM CAMPANHA").astype(str).str.strip().str.upper()
    return df

def ultima_linha_por_lead(df: pd.DataFrame) -> pd.DataFrame:
    df2 = df.sort_values(["LEAD_KEY", "DIA"]).copy()
    ult = df2.groupby("LEAD_KEY", as_index=False).tail(1).copy()
    ult["ULTIMA_ATUALIZACAO"] = ult["DIA"]
    return ult

def flags_por_lead(df_hist: pd.DataFrame) -> pd.DataFrame:
    """Marca se o lead 'passou' por cada etapa em QUALQUER momento (para conversão correta)."""
    g = df_hist.groupby("LEAD_KEY")
    out = pd.DataFrame({
        "LEAD_KEY": g.size().index,
        "PASSOU_EM_ANALISE": g["STATUS_BASE"].apply(lambda s: (s == "EM ANÁLISE").any()).values,
        "PASSOU_REANALISE": g["STATUS_BASE"].apply(lambda s: (s == "REANÁLISE").any()).values,
        "PASSOU_APROVACAO": g["STATUS_BASE"].apply(lambda s: (s == "APROVAÇÃO").any()).values,
        "PASSOU_BACEN": g["STATUS_BASE"].apply(lambda s: (s == "APROVADO BACEN").any()).values,
        "PASSOU_REPROVACAO": g["STATUS_BASE"].apply(lambda s: (s == "REPROVAÇÃO").any()).values,
        "PASSOU_PENDENCIA": g["STATUS_BASE"].apply(lambda s: (s == "PENDÊNCIA").any()).values,
        "PASSOU_VENDA_GERADA": g["STATUS_BASE"].apply(lambda s: (s == "VENDA GERADA").any()).values,
        "PASSOU_VENDA_INFORMADA": g["STATUS_BASE"].apply(lambda s: (s == "VENDA INFORMADA").any()).values,
        "PASSOU_DESISTIU": g["STATUS_BASE"].apply(lambda s: (s == "DESISTIU").any()).values,
    })
    return out

# =========================
# LOAD
# =========================
df_plan = carregar_planilha()
df_crm = carregar_crm_ultimos_1000()
df_raw = aplicar_origem_crm(df_plan, df_crm)

# =========================
# FILTROS (Data / Data Base / Equipe / Corretor)
# =========================
st.subheader("🧰 Filtros")

col1, col2, col3 = st.columns([2.2, 1.6, 1.6])

with col1:
    datas_validas = df_raw["DIA"].dropna()
    if len(datas_validas) == 0:
        st.error("Sua planilha não tem datas válidas na coluna DATA/DIA.")
        st.stop()

    dt_min = datas_validas.min().date()
    dt_max = datas_validas.max().date()
    periodo = st.date_input("Período (Data)", value=(dt_min, dt_max), min_value=dt_min, max_value=dt_max)

    if isinstance(periodo, (list, tuple)) and len(periodo) == 2:
        dt_ini, dt_fim = periodo
    else:
        dt_ini, dt_fim = dt_min, dt_max

with col2:
    bases = sorted([b for b in df_raw["DATA_BASE"].dropna().unique().tolist() if str(b).strip() != ""])
    base_sel = st.selectbox("Data Base (mês comercial)", ["TODAS"] + bases, index=0)

with col3:
    equipes = sorted([e for e in df_raw["EQUIPE"].dropna().unique().tolist() if str(e).strip() != ""])
    equipe_sel = st.selectbox("Equipe", ["TODAS"] + equipes, index=0)

df_filtrado = df_raw.copy()
df_filtrado = df_filtrado[(df_filtrado["DIA"].dt.date >= dt_ini) & (df_filtrado["DIA"].dt.date <= dt_fim)]
if base_sel != "TODAS":
    df_filtrado = df_filtrado[df_filtrado["DATA_BASE"] == base_sel]
if equipe_sel != "TODAS":
    df_filtrado = df_filtrado[df_filtrado["EQUIPE"] == equipe_sel]

corretores = sorted([c for c in df_filtrado["CORRETOR"].dropna().unique().tolist() if str(c).strip() != ""])
corretor_sel = st.selectbox("Corretor", ["TODOS"] + corretores, index=0)
if corretor_sel != "TODOS":
    df_filtrado = df_filtrado[df_filtrado["CORRETOR"] == corretor_sel]

# base “atual” (última linha por lead) dentro do período
df_ult = ultima_linha_por_lead(df_filtrado)

# =========================
# STATUS ATUAL DO FUNIL (último status)
# =========================
st.markdown("---")
st.subheader("📌 Status Atual do Funil")

def count_status_ult(status: str) -> int:
    return int((df_ult["STATUS_BASE"] == status).sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric("Em Análise", count_status_ult("EM ANÁLISE"))
c2.metric("Reanálises", count_status_ult("REANÁLISE"))
c3.metric("Pendências", count_status_ult("PENDÊNCIA"))
c4.metric("Vendas Geradas", count_status_ult("VENDA GERADA"))

c5, c6, c7, c8 = st.columns(4)
c5.metric("Aprovação", count_status_ult("APROVAÇÃO"))
c6.metric("Aprovado Bacen", count_status_ult("APROVADO BACEN"))
c7.metric("Reprovação", count_status_ult("REPROVAÇÃO"))
c8.metric("Vendas Informadas", count_status_ult("VENDA INFORMADA"))

st.metric("Leads Ativos no Funil", len(df_ult))

# =========================
# PERFORMANCE & CONVERSÃO POR ORIGEM (CONVERSÃO DE VERDADE)
# =========================
st.markdown("---")
st.subheader("📈 Performance e Conversão por Origem")

origens = sorted([o for o in df_ult["ORIGEM"].dropna().unique().tolist() if str(o).strip() != ""])
origem_sel = st.selectbox("Origem", ["TODAS"] + origens, index=0)

tipo_venda = st.radio(
    "Tipo de Venda para Conversão",
    ["Vendas Geradas + Informadas", "Apenas Vendas Geradas"],
    horizontal=True
)

df_ult_origem = df_ult.copy()
if origem_sel != "TODAS":
    df_ult_origem = df_ult_origem[df_ult_origem["ORIGEM"] == origem_sel]

keys_origem = set(df_ult_origem["LEAD_KEY"].tolist())
df_hist_origem = df_filtrado[df_filtrado["LEAD_KEY"].isin(keys_origem)].copy()

df_flags = flags_por_lead(df_hist_origem)
df_flags = df_flags[df_flags["LEAD_KEY"].isin(keys_origem)].copy()

leads_total = len(df_flags)
q_analises = int(df_flags["PASSOU_EM_ANALISE"].sum())
q_aprov = int(df_flags["PASSOU_APROVACAO"].sum())
q_bacen = int(df_flags["PASSOU_BACEN"].sum())
q_reanalises = int(df_flags["PASSOU_REANALISE"].sum())
q_reprov = int(df_flags["PASSOU_REPROVACAO"].sum())
q_pend = int(df_flags["PASSOU_PENDENCIA"].sum())

venda_sem_duplicar = (df_flags["PASSOU_VENDA_GERADA"]) | (df_flags["PASSOU_VENDA_INFORMADA"] & (~df_flags["PASSOU_VENDA_GERADA"]))
if tipo_venda == "Apenas Vendas Geradas":
    q_vendas = int(df_flags["PASSOU_VENDA_GERADA"].sum())
else:
    q_vendas = int(venda_sem_duplicar.sum())

colA, colB, colC, colD = st.columns(4)
colA.metric("Leads", leads_total)
colB.metric("Análises (passou em EM ANÁLISE)", q_analises)
colC.metric("Reanálises (passou)", q_reanalises)
colD.metric("Vendas", q_vendas)

colE, colF, colG, colH = st.columns(4)
colE.metric("Aprovação (passou)", q_aprov)
colF.metric("Aprov. Bacen (passou)", q_bacen)
colG.metric("Reprovação (passou)", q_reprov)
colH.metric("Pendência (passou)", q_pend)

colI, colJ, colK, colL = st.columns(4)
colI.metric("Lead → Análise", f"{pct(q_analises, leads_total)}%")
colJ.metric("Análise → Aprovação", f"{pct(q_aprov, q_analises)}%")
colK.metric("Análise → Venda", f"{pct(q_vendas, q_analises)}%")
colL.metric("Aprovação → Venda", f"{pct(q_vendas, q_aprov)}%")

st.markdown("### 🧾 Leads da Origem Selecionada (última atualização)")
cols_show = ["CLIENTE", "CORRETOR", "EQUIPE", "ORIGEM", "STATUS_BASE", "ULTIMA_ATUALIZACAO"]
df_tbl = df_ult_origem[cols_show].sort_values("ULTIMA_ATUALIZACAO", ascending=False).copy()
st.dataframe(df_tbl, use_container_width=True, hide_index=True)

# =========================
# PESQUISA / AUDITORIA DE LEAD (cards + linha do tempo)
# =========================
st.markdown("---")
st.subheader("🔎 Buscar Lead (cards + linha do tempo)")

busca_col1, busca_col2 = st.columns([1.1, 3])
with busca_col1:
    modo_busca = st.radio("Buscar por:", ["Nome", "CPF"], horizontal=True)
with busca_col2:
    termo = st.text_input("Digite para buscar", value="")

def montar_card_cliente(df_hist: pd.DataFrame):
    df_hist = df_hist.sort_values("DIA")
    last = df_hist.tail(1).iloc[0]

    cliente = last["CLIENTE"]
    cpf = last.get("CPF", "")
    cpf = cpf if str(cpf).strip() else "NÃO INFORMADO"
    situ = last["STATUS_BASE"]
    corretor = last.get("CORRETOR", "—")
    equipe = last.get("EQUIPE", "—")
    origem = last.get("ORIGEM", "—")
    ultima = last["DIA"].date() if pd.notna(last["DIA"]) else "—"
    obs = (str(last.get("OBS", "")).strip() + "\n" + str(last.get("OBS2", "")).strip()).strip()
    obs = obs if obs else "—"

    st.markdown(f"## 👤 {cliente}")
    st.write(f"**CPF:** `{cpf}`")
    st.write(f"**Última movimentação:** `{ultima}`")
    st.write(f"**Situação atual:** `{situ}`")
    st.write(f"**Corretor responsável:** `{corretor}`")
    st.write(f"**Equipe:** `{equipe}`")
    st.write(f"**Origem (CRM):** `{origem}`")
    st.write("**Última observação:**")
    st.info(obs)

    st.markdown("### 📜 Linha do tempo")
    timeline_cols = ["DIA", "STATUS_BASE", "CORRETOR", "EQUIPE", "OBS", "OBS2"]
    tl = df_hist[timeline_cols].copy()
    tl["DIA"] = tl["DIA"].dt.strftime("%d/%m/%Y")
    st.dataframe(tl.sort_values("DIA"), use_container_width=True, hide_index=True)

if termo.strip():
    if modo_busca == "CPF":
        termo_norm = re.sub(r"\D+", "", termo)
        df_hist = df_filtrado[df_filtrado["CPF_NORM"] == termo_norm].copy()
    else:
        termo_norm = normalizar_texto(termo)
        df_hist = df_filtrado[df_filtrado["CLIENTE_NORM"].str.contains(termo_norm, na=False)].copy()

    if df_hist.empty:
        st.warning("Nenhum lead encontrado com esse filtro dentro do período selecionado.")
    else:
        op = df_hist.sort_values("DIA", ascending=False)[["LEAD_KEY", "CLIENTE"]].drop_duplicates("LEAD_KEY")
        if len(op) > 1:
            escolha = st.selectbox("Escolha o lead", op["CLIENTE"].tolist())
            df_hist = df_hist[df_hist["CLIENTE"] == escolha].copy()
        montar_card_cliente(df_hist)
