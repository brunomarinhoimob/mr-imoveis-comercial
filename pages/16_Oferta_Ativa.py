import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
from fpdf import FPDF
if "logado" not in st.session_state or not st.session_state.logado:
    st.warning("🔒 Acesso restrito. Faça login para continuar.")
    st.stop()
# ---------------------------------------------------------
# BLOQUEIO DE PERFIL CORRETOR
# ---------------------------------------------------------
if st.session_state.get("perfil") == "corretor":
    st.warning("🔒 Você não tem permissão para acessar esta página.")
    st.stop()

from utils.supremo_config import TOKEN_SUPREMO

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Oferta Ativa – Leads pra Ligar",
    page_icon="📞",
    layout="wide",
)

st.title("📞 Oferta Ativa – Leads pra Ligar")
st.caption("Base limpa de leads do CRM, pronta para contato ativo.")

# ---------------------------------------------------------
# FUNÇÃO – BUSCAR LEADS NO SUPREMO CRM
# ---------------------------------------------------------
@st.cache_data(ttl=1800)
def carregar_leads_oferta(limit=3000, max_pages=200):
    url = "https://api.supremocrm.com.br/v1/leads"
    headers = {"Authorization": f"Bearer {TOKEN_SUPREMO}"}

    dados = []
    pagina = 1

    while pagina <= max_pages and len(dados) < limit:
        resp = requests.get(
            url,
            headers=headers,
            params={"pagina": pagina},
            timeout=30,
        )
        if resp.status_code != 200:
            break

        js = resp.json()
        if not js.get("data"):
            break

        dados.extend(js["data"])
        pagina += 1

    if not dados:
        return pd.DataFrame()

    df = pd.DataFrame(dados).drop_duplicates(subset=["id"])

    # Normalização
    df["NOME"] = df.get("nome_pessoa", "").fillna("").astype(str).str.upper().str.strip()
    df["TELEFONE"] = df.get("telefone_pessoa", "").fillna("").astype(str).str.strip()
    df["ORIGEM"] = df.get("nome_origem", "").fillna("").astype(str).str.upper().str.strip()
    df["CAMPANHA"] = df.get("nome_campanha", "").fillna("").astype(str).str.upper().str.strip()
    df["CORRETOR"] = df.get("nome_corretor", "").fillna("").astype(str).str.upper().str.strip()

    df["DATA_CAPTURA"] = pd.to_datetime(df.get("data_captura"), errors="coerce")
    df = df.dropna(subset=["DATA_CAPTURA"])

    # -----------------------------------------------------
    # REGRAS DE NEGÓCIO – OFERTA ATIVA
    # -----------------------------------------------------
    origem_upper = df["ORIGEM"]

    mask_excluir_origem = (
        origem_upper.str.contains("CARTEIRA", na=False)
        | origem_upper.str.contains("INDICA", na=False)
        | origem_upper.str.contains("IMPULSIONAMENTO CORRETOR", na=False)
    )

    df = df[~mask_excluir_origem]

    palavras_finalizacao = ["VENDA", "COMPROU", "CLIENTE", "FINALIZ", "CONCLU"]

    for termo in palavras_finalizacao:
        df = df[
            ~df["ORIGEM"].str.contains(termo, na=False)
            & ~df["CAMPANHA"].str.contains(termo, na=False)
        ]

    return df.reset_index(drop=True)

# ---------------------------------------------------------
# CARREGAMENTO DOS LEADS
# ---------------------------------------------------------
st.sidebar.title("Filtros – Oferta Ativa")

usar_api = st.sidebar.checkbox("Buscar direto do CRM", value=True)

if usar_api:
    limite = st.sidebar.slider("Quantidade máxima de leads", 1000, 5000, 3000, 500)
    df = carregar_leads_oferta(limit=limite)
else:
    df = st.session_state.get("df_leads", pd.DataFrame())

if df is None or df.empty:
    st.error("Nenhum lead disponível.")
    st.stop()

# ---------------------------------------------------------
# FILTROS
# ---------------------------------------------------------
hoje = datetime.now().date()

data_ini = st.sidebar.date_input("Data inicial", hoje - timedelta(days=7))
data_fim = st.sidebar.date_input("Data final", hoje)

if data_ini > data_fim:
    data_ini, data_fim = data_fim, data_ini

df = df[
    (df["DATA_CAPTURA"].dt.date >= data_ini)
    & (df["DATA_CAPTURA"].dt.date <= data_fim)
]

corretores = sorted(df["CORRETOR"].dropna().unique())
corretor_sel = st.sidebar.selectbox("Corretor", ["Todos"] + corretores)

if corretor_sel != "Todos":
    df = df[df["CORRETOR"] == corretor_sel]

if df.empty:
    st.warning("Nenhum lead para os filtros selecionados.")
    st.stop()

# ---------------------------------------------------------
# KPI
# ---------------------------------------------------------
st.subheader("📊 Resumo")

c1, c2, c3 = st.columns(3)
c1.metric("Leads disponíveis", len(df))
c2.metric("Corretores", df["CORRETOR"].nunique())
c3.metric("Período", f"{data_ini} → {data_fim}")

# ---------------------------------------------------------
# TABELA
# ---------------------------------------------------------
st.divider()
st.subheader("📋 Leads para contato")

tabela = df[["NOME", "TELEFONE", "ORIGEM", "CAMPANHA"]].copy()
st.dataframe(tabela, use_container_width=True)

# ---------------------------------------------------------
# PDF
# ---------------------------------------------------------
def limpar_texto_pdf(texto):
    if pd.isna(texto):
        return ""
    return (
        str(texto)
        .encode("latin-1", errors="ignore")
        .decode("latin-1")
    )

def gerar_pdf(df_pdf):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=10)

    # 🔧 AJUSTE AQUI
    linhas_por_pagina = 33  # máximo 33 linhas por página

    col_nome = 70
    col_tel = 40
    col_obs = 80

    for i in range(0, len(df_pdf), linhas_por_pagina):
        pdf.add_page()
        pdf.set_font("Arial", "B", 10)

        pdf.cell(col_nome, 8, "NOME", border=1)
        pdf.cell(col_tel, 8, "TELEFONE", border=1)
        pdf.cell(col_obs, 8, "INFORMAÇÕES", border=1)
        pdf.ln()

        pdf.set_font("Arial", size=9)

        bloco = df_pdf.iloc[i:i + linhas_por_pagina]

        for _, row in bloco.iterrows():
            nome = limpar_texto_pdf(row["NOME"])
            telefone = limpar_texto_pdf(row["TELEFONE"])

            pdf.cell(col_nome, 8, nome[:40], border=1)
            pdf.cell(col_tel, 8, telefone[:20], border=1)
            pdf.cell(col_obs, 8, "", border=1)
            pdf.ln()

    return bytes(pdf.output(dest="S"))




st.divider()

if st.button("📄 Gerar PDF para Oferta Ativa"):
    pdf_bytes = gerar_pdf(df[["NOME", "TELEFONE"]])
    st.download_button(
        "⬇️ Baixar PDF",
        data=pdf_bytes,
        file_name="oferta_ativa_leads.pdf",
        mime="application/pdf",
    )
