import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
from fpdf import FPDF

from utils.supremo_config import TOKEN_SUPREMO

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Oferta Ativa – Leads pra Ligar",
    page_icon="📞",
    layout="wide",
)

st.title("📞 Oferta Ativa – Base de Leads para Contato")
st.caption(
    "Filtra os últimos leads por período, exclui carteira de corretor e indicação, "
    "e gera um PDF pronto para oferta ativa."
)

# ---------------------------------------------------------
# FUNÇÃO PARA BUSCAR LEADS DIRETO DO CRM (MAIS LEADS)
# ---------------------------------------------------------
BASE_URL_LEADS = "https://api.supremocrm.com.br/v1/leads"


@st.cache_data(ttl=3600)
def carregar_leads_oferta(limit: int = 3000, max_pages: int = 200) -> pd.DataFrame:
    """
    Busca leads direto da API do Supremo, permitindo limites grandes (ex.: 3000, 4000, 5000).
    """
    headers = {"Authorization": f"Bearer {TOKEN_SUPREMO}"}

    dfs = []
    total = 0
    pagina = 1

    while total < limit and pagina <= max_pages:
        params = {"pagina": pagina}
        try:
            resp = requests.get(
                BASE_URL_LEADS,
                headers=headers,
                params=params,
                timeout=30,
            )
        except Exception:
            break

        if resp.status_code != 200:
            break

        try:
            data = resp.json()
        except Exception:
            break

        if isinstance(data, dict) and "data" in data:
            df_page = pd.DataFrame(data["data"])
        elif isinstance(data, list):
            df_page = pd.DataFrame(data)
        else:
            df_page = pd.DataFrame()

        if df_page.empty:
            break

        dfs.append(df_page)
        total += len(df_page)
        pagina += 1

    if not dfs:
        return pd.DataFrame()

    df_all = pd.concat(dfs, ignore_index=True)

    # Remove duplicados por ID, se tiver
    if "id" in df_all.columns:
        df_all = df_all.drop_duplicates(subset="id")

    # Data de captura + campo date normalizado
    if "data_captura" in df_all.columns:
        df_all["data_captura"] = pd.to_datetime(
            df_all["data_captura"], errors="coerce"
        )
        df_all["data_captura_date"] = df_all["data_captura"].dt.date
    else:
        df_all["data_captura_date"] = pd.NaT

    # Nome do corretor normalizado (mesmo padrão do app_dashboard)
    if "nome_corretor" in df_all.columns:
        df_all["nome_corretor_norm"] = (
            df_all["nome_corretor"]
            .fillna("NÃO INFORMADO")
            .astype(str)
            .str.upper()
            .str.strip()
        )
    else:
        df_all["nome_corretor_norm"] = "NÃO INFORMADO"

    # Equipe (se existir)
    possiveis_equipes = ["equipe", "nome_equipe", "equipe_nome", "nome_equipe_lead"]
    col_equipe = next((c for c in possiveis_equipes if c in df_all.columns), None)
    if col_equipe:
        df_all["equipe_lead_norm"] = (
            df_all[col_equipe]
            .fillna("NÃO INFORMADO")
            .astype(str)
            .str.upper()
            .str.strip()
        )
    else:
        df_all["equipe_lead_norm"] = "NÃO INFORMADO"

    return df_all.head(limit)


# ---------------------------------------------------------
# CARREGA BASE DE LEADS (SESSÃO OU CRM DIRETO)
# ---------------------------------------------------------
df_leads_sessao = st.session_state.get("df_leads", pd.DataFrame())

st.sidebar.title("Filtros – Oferta Ativa")
st.sidebar.markdown("### Fonte dos leads")

usar_api_direta = st.sidebar.checkbox(
    "Buscar direto do CRM (pode trazer mais leads)",
    value=False,
)

if usar_api_direta:
    limite_api = st.sidebar.slider(
        "Limite de leads para buscar do CRM",
        min_value=1000,
        max_value=5000,
        value=3000,
        step=500,
    )
    df_leads = carregar_leads_oferta(limit=limite_api)
else:
    df_leads = df_leads_sessao
    if df_leads is None or df_leads.empty:
        st.warning(
            "Base de leads da sessão está vazia. "
            "Buscando direto do CRM com limite padrão de 3000 leads."
        )
        df_leads = carregar_leads_oferta(limit=3000)

if df_leads is None or df_leads.empty:
    st.error("Não foi possível carregar leads do CRM.")
    st.stop()

df = df_leads.copy()

# ---------------------------------------------------------
# NORMALIZAÇÃO BÁSICA
# ---------------------------------------------------------
# Nome do lead
col_nome = next(
    (c for c in ["nome_pessoa", "nome", "nome_cliente"] if c in df.columns),
    None,
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
col_tel = next(
    (c for c in ["telefone_pessoa", "telefone", "phone"] if c in df.columns),
    None,
)
if col_tel is None:
    df["TELEFONE_LEAD"] = ""
else:
    df["TELEFONE_LEAD"] = df[col_tel].fillna("").astype(str).str.strip()

# Corretor
col_corretor = next(
    (c for c in ["nome_corretor_norm", "nome_corretor"] if c in df.columns),
    None,
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

# Origem / campanha
col_origem = "nome_origem" if "nome_origem" in df.columns else None
col_campanha = "nome_campanha" if "nome_campanha" in df.columns else None

# Data captura
if "data_captura_date" in df.columns:
    df["DATA_CAPTURA_DT"] = pd.to_datetime(df["data_captura_date"], errors="coerce")
elif "data_captura" in df.columns:
    df["DATA_CAPTURA_DT"] = pd.to_datetime(df["data_captura"], errors="coerce")
else:
    df["DATA_CAPTURA_DT"] = pd.NaT

df = df[df["DATA_CAPTURA_DT"].notna()].copy()
if df.empty:
    st.error("Não há leads com data de captura válida.")
    st.stop()

# ---------------------------------------------------------
# REMOVE CARTEIRA CORRETOR / INDICAÇÃO
# ---------------------------------------------------------
if col_origem:
    origem_upper = df[col_origem].fillna("").astype(str).str.upper()
    mask_excluir = (
        origem_upper.str.contains("CARTEIRA")
        | origem_upper.str.contains("INDICAÇÃO")
        | origem_upper.str.contains("INDICACAO")
    )
    df = df[~mask_excluir].copy()

# ---------------------------------------------------------
# FILTROS – PERÍODO / QTD / CORRETOR
# ---------------------------------------------------------
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

limite_leads = st.sidebar.slider(
    "Quantidade máxima de leads para oferta ativa",
    min_value=50,
    max_value=2000,
    value=300,
    step=50,
)

lista_corretor = sorted(df["CORRETOR_EXIBICAO"].dropna().unique())
corretor_sel = st.sidebar.selectbox(
    "Filtrar por corretor (opcional)",
    ["Todos"] + lista_corretor,
)

mask_periodo = (df["DATA_CAPTURA_DT"].dt.date >= data_ini) & (
    df["DATA_CAPTURA_DT"].dt.date <= data_fim
)
df_periodo = df[mask_periodo].copy()
if corretor_sel != "Todos":
    df_periodo = df_periodo[df_periodo["CORRETOR_EXIBICAO"] == corretor_sel]

if df_periodo.empty:
    st.warning("Nenhum lead encontrado para os filtros selecionados.")
    st.stop()

df_periodo = df_periodo.sort_values("DATA_CAPTURA_DT", ascending=False)
df_oferta = df_periodo.head(limite_leads).copy()

st.caption(
    f"Período: **{data_ini.strftime('%d/%m/%Y')}** até **{data_fim.strftime('%d/%m/%Y')}** • "
    f"Leads após filtros (sem carteira/indicação): **{len(df_periodo)}** • "
    f"Exibindo para oferta ativa: **{len(df_oferta)}**"
    + (f" • Corretor: **{corretor_sel}**" if corretor_sel != "Todos" else "")
)

# ---------------------------------------------------------
# TABELA FORMATADA (VISUAL NO DASHBOARD)
# ---------------------------------------------------------
st.markdown("## 📋 Base de Oferta Ativa")

colunas_oferta = [
    "NOME_LEAD",
    "TELEFONE_LEAD",
    "DATA_CAPTURA_DT",
    "CORRETOR_EXIBICAO",
]
if col_origem:
    colunas_oferta.append(col_origem)
if col_campanha:
    colunas_oferta.append(col_campanha)

df_tab = df_oferta[colunas_oferta].copy()
df_tab = df_tab.rename(
    columns={
        "NOME_LEAD": "Lead",
        "TELEFONE_LEAD": "Telefone",
        "DATA_CAPTURA_DT": "Data captura",
        "CORRETOR_EXIBICAO": "Corretor",
        col_origem: "Origem" if col_origem else col_origem,
        col_campanha: "Campanha" if col_campanha else col_campanha,
    }
)
df_tab["Data captura"] = pd.to_datetime(
    df_tab["Data captura"], errors="coerce"
).dt.strftime("%d/%m/%Y %H:%M")

st.dataframe(df_tab, use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# FUNÇÃO PDF (LIMPANDO CARACTERES FORA DO LATIN-1)
# ---------------------------------------------------------
def gerar_pdf_oferta(df_pdf: pd.DataFrame, titulo: str) -> bytes:
    def to_pdf_text(texto):
        # garante string e remove caracteres fora do latin-1
        return str(texto).encode("latin-1", "ignore").decode("latin-1")

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()

    # Título
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, to_pdf_text(titulo), ln=True, align="C")
    pdf.ln(4)

    # Info total
    pdf.set_font("Arial", "", 10)
    info_total = f"Total de leads nesta base: {len(df_pdf)}"
    pdf.cell(0, 6, to_pdf_text(info_total), ln=True, align="L")
    pdf.ln(2)

    # Cabeçalho
    pdf.set_font("Arial", "B", 10)
    colunas = list(df_pdf.columns)
    largura_total = 280  # largura útil A4 landscape
    col_width = largura_total / len(colunas)

    for col in colunas:
        pdf.cell(col_width, 8, to_pdf_text(col)[:30], border=1, align="C")
    pdf.ln(8)

    # Linhas
    pdf.set_font("Arial", "", 9)
    for _, row in df_pdf.iterrows():
        for col in colunas:
            valor = row[col] if col in row else ""
            txt = to_pdf_text(valor).replace("\n", " ")
            if len(txt) > 40:
                txt = txt[:37] + "..."
            pdf.cell(col_width, 7, txt, border=1)
        pdf.ln(7)

    data = pdf.output(dest="S")
    if isinstance(data, bytearray):
        return bytes(data)
    return data


# ---------------------------------------------------------
# MONTAGEM DO DATAFRAME ESPECÍFICO PARA O PDF
# (Lead, Telefone, Origem, Informações em branco)
# ---------------------------------------------------------
df_pdf = df_tab.copy()

# garante coluna Origem
if "Origem" not in df_pdf.columns:
    df_pdf["Origem"] = ""

# adiciona coluna em branco para anotações
df_pdf["Informações"] = ""

df_pdf = df_pdf[["Lead", "Telefone", "Origem", "Informações"]]

# ---------------------------------------------------------
# DOWNLOAD – APENAS PDF
# ---------------------------------------------------------
st.markdown("---")
st.markdown("## ⬇️ Download da base para oferta ativa (PDF)")

pdf_bytes = gerar_pdf_oferta(
    df_pdf,
    titulo=f"Oferta ativa - {data_ini.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}",
)

st.download_button(
    label="🧾 Baixar PDF para oferta ativa",
    data=pdf_bytes,
    file_name=f"oferta_ativa_{data_ini.strftime('%Y%m%d')}_{data_fim.strftime('%Y%m%d')}.pdf",
    mime="application/pdf",
)

st.markdown(
    "<p style='text-align:center; color:#6b7280; margin-top:1rem;'>"
    "PDF pronto para rodar oferta ativa – ligações, WhatsApp e campanhas."
    "</p>",
    unsafe_allow_html=True,
)
