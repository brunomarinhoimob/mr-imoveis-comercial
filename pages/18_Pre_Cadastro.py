# =========================================================
# PRÉ-CADASTRO – ANÁLISES PENDENTES (ÚLTIMOS 7 DIAS)
# REGRA: CLIENTE + CORRETOR
# <= 60 DIAS  -> REANÁLISE
# >  60 DIAS  -> NOVA ANÁLISE
# PÁGINA OFICIAL 18
# =========================================================

import streamlit as st
import pandas as pd
import requests
import unicodedata
from datetime import datetime, timedelta

from streamlit_autorefresh import st_autorefresh
from utils.supremo_config import TOKEN_SUPREMO
from app_dashboard import carregar_dados_planilha

# =========================================================
# TRAVA DE LOGIN
# =========================================================
if not st.session_state.get("logado"):
    st.stop()

if st.session_state.get("perfil") == "corretor":
    st.error("⛔ Acesso restrito aos gestores.")
    st.stop()

# =========================================================
# CONFIG DA PÁGINA
# =========================================================
st.set_page_config(
    page_title="Pré-Cadastro | Análises Pendentes",
    page_icon="📂",
    layout="wide"
)

st.title("📂 Pré-Cadastro – Análises Pendentes")

# =========================================================
# AUTO REFRESH (30s – SEM F5)
# =========================================================
st_autorefresh(interval=30 * 1000, key="auto_refresh_pre_cadastro_18")

# =========================================================
# CONFIGURAÇÕES
# =========================================================
API_URL = "https://api.supremocrm.com.br/v1/leads"
HEADERS = {"Authorization": f"Bearer {TOKEN_SUPREMO}"}

SITUACAO_ALVO = "ANALISE PENDENTE"
DIAS_JANELA_CRM = 7        # limite técnico
LIMITE_REANALISE = 60      # REGRA OFICIAL

# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================
def normalizar(txt):
    if pd.isna(txt):
        return ""
    txt = str(txt).strip().upper()
    txt = unicodedata.normalize("NFKD", txt).encode("ASCII", "ignore").decode("ASCII")
    return txt

# =========================================================
# CARGA DOS LEADS DO CRM (ÚLTIMOS 7 DIAS)
# =========================================================
@st.cache_data(ttl=30)
def carregar_leads_crm():
    dados = []
    pagina = 1
    data_limite = datetime.now() - timedelta(days=DIAS_JANELA_CRM)

    while True:
        r = requests.get(
            API_URL,
            headers=HEADERS,
            params={"pagina": pagina},
            timeout=20
        )

        if r.status_code != 200:
            break

        js = r.json()
        if not js.get("data"):
            break

        for lead in js["data"]:
            data_captura = pd.to_datetime(lead.get("data_captura"), errors="coerce")

            if pd.isna(data_captura):
                continue

            if data_captura < data_limite:
                return pd.DataFrame(dados)

            dados.append(lead)

        pagina += 1

    return pd.DataFrame(dados)

# =========================================================
# LOAD DOS DADOS
# =========================================================
df_leads = carregar_leads_crm()
df_plan = carregar_dados_planilha()

if df_leads.empty:
    st.success("🎉 Nenhuma análise pendente no momento.")
    st.stop()

# =========================================================
# NORMALIZAÇÃO DAS CHAVES
# =========================================================
df_leads["CLIENTE_KEY"] = df_leads["nome_pessoa"].apply(normalizar)
df_leads["CORRETOR_KEY"] = df_leads["nome_corretor"].apply(normalizar)

df_plan["CLIENTE_KEY"] = df_plan["CLIENTE"].apply(normalizar)
df_plan["CORRETOR_KEY"] = df_plan["CORRETOR"].apply(normalizar)

# =========================================================
# DATA REAL DA ANÁLISE (COLUNA A DA PLANILHA) — parse BR robusto
# =========================================================
df_plan["DATA"] = df_plan["DATA"].astype(str).str.strip()

dt1 = pd.to_datetime(df_plan["DATA"], errors="coerce", dayfirst=True)  # dd/mm/yyyy
dt2 = pd.to_datetime(df_plan["DATA"], errors="coerce")                # fallback
df_plan["DATA"] = dt1.fillna(dt2)

# =========================================================
# FILTRO – SOMENTE ANÁLISE PENDENTE
# =========================================================
df = df_leads[
    df_leads["nome_situacao"].astype(str).str.upper() == SITUACAO_ALVO
].copy()

# =========================================================
# CLASSIFICAÇÃO: NOVA x REANÁLISE (REGRA 60 DIAS)
# =========================================================
def classificar_analise(row):
    registros = df_plan[
        (df_plan["CLIENTE_KEY"] == row["CLIENTE_KEY"]) &
        (df_plan["CORRETOR_KEY"] == row["CORRETOR_KEY"])
    ]

    if registros.empty:
        return "NOVA"

    ultima_data = registros["DATA"].max()

    if pd.isna(ultima_data):
        return "NOVA"

    dias = (pd.Timestamp.now().normalize() - ultima_data.normalize()).days

    return "REANÁLISE" if dias <= LIMITE_REANALISE else "NOVA"

df["TIPO_ANALISE"] = df.apply(classificar_analise, axis=1)

# =========================================================
# ORDENAÇÃO – FIFO REAL
# =========================================================
df["DATA_CAPTURA"] = pd.to_datetime(df["data_captura"], errors="coerce")
df = df.sort_values("DATA_CAPTURA")

# =========================================================
# TOPO – CONTADOR
# =========================================================
st.markdown(f"## ⏳ Tem **{len(df)} análises** para subir")
st.divider()

# =========================================================
# CARDS
# =========================================================
cols = st.columns(3)

for i, row in df.iterrows():
    with cols[i % 3]:

        badge = "🆕 NOVA ANÁLISE" if row["TIPO_ANALISE"] == "NOVA" else "🔁 REANÁLISE"
        border = "#22c55e" if row["TIPO_ANALISE"] == "NOVA" else "#f59e0b"

        obs = row.get("anotacoes", "")
        obs = obs[:200] + "..." if len(str(obs)) > 200 else obs

        data_cap = "-"
        if pd.notna(row.get("DATA_CAPTURA")):
            data_cap = row["DATA_CAPTURA"].strftime("%d/%m/%Y")

        st.markdown(
            f"""
            <div style="
                border: 2px solid {border};
                border-radius: 14px;
                padding: 16px;
                margin-bottom: 18px;
            ">
                <h4>{row['nome_pessoa']}</h4>
                <strong>{badge}</strong><br><br>

                📧 {row.get('email_pessoa','-')}<br>
                📞 {row.get('telefone_pessoa','-')}<br>
                👤 {row.get('nome_corretor','-')}<br>
                🕒 {data_cap}<br><br>

                📝 {obs}<br><br>

                📌 Situação: {row.get('nome_situacao','-')}
            </div>
            """,
            unsafe_allow_html=True
        )
