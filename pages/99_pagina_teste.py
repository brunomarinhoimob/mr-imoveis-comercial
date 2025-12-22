# =========================================================
# PRÉ-CADASTRO – ANÁLISES PENDENTES (30 DIAS DE CAPTURA)
# =========================================================

import streamlit as st
import pandas as pd
import requests
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
# AUTO REFRESH (SEM F5)
# =========================================================
st_autorefresh(interval=30 * 1000, key="auto_refresh_pre_cadastro")

# =========================================================
# CONFIG
# =========================================================
API_URL = "https://api.supremocrm.com.br/v1/leads"
HEADERS = {"Authorization": f"Bearer {TOKEN_SUPREMO}"}

SITUACAO_ALVO = "ANALISE PENDENTE"
DIAS_JANELA = 30

# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================
def normalizar(txt):
    if pd.isna(txt):
        return ""
    return str(txt).strip().upper()

# =========================================================
# CARGA CRM (LIMITADA POR DATA DE CAPTURA)
# =========================================================
@st.cache_data(ttl=30)
def carregar_leads_crm():
    dados = []
    pagina = 1
    data_limite = datetime.now() - timedelta(days=DIAS_JANELA)

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
            data_captura = pd.to_datetime(
                lead.get("data_captura"), errors="coerce"
            )

            # se não tem data, ignora
            if pd.isna(data_captura):
                continue

            # se passou da janela, pode parar (leads vêm ordenados por data)
            if data_captura < data_limite:
                return pd.DataFrame(dados)

            dados.append(lead)

        pagina += 1

    return pd.DataFrame(dados)

# =========================================================
# LOAD DADOS
# =========================================================
df_leads = carregar_leads_crm()
df_plan = carregar_dados_planilha()

if df_leads.empty:
    st.success("🎉 Nenhuma análise pendente no momento.")
    st.stop()

# =========================================================
# NORMALIZA CHAVES (ANTI-REANÁLISE)
# =========================================================
df_leads["CLIENTE_KEY"] = df_leads["nome_pessoa"].apply(normalizar)
df_leads["CORRETOR_KEY"] = df_leads["nome_corretor"].apply(normalizar)

df_plan["CLIENTE_KEY"] = df_plan["CLIENTE"].apply(normalizar)
df_plan["CORRETOR_KEY"] = df_plan["CORRETOR"].apply(normalizar)

# =========================================================
# FILTRO – ANALISE PENDENTE (REGRA DE NEGÓCIO)
# =========================================================
df = df_leads[
    df_leads["nome_situacao"].astype(str).str.upper() == SITUACAO_ALVO
].copy()

# =========================================================
# MARCA REANÁLISE
# =========================================================
df["TIPO_ANALISE"] = df.apply(
    lambda r: "REANÁLISE"
    if (
        (df_plan["CLIENTE_KEY"] == r["CLIENTE_KEY"]) &
        (df_plan["CORRETOR_KEY"] == r["CORRETOR_KEY"])
    ).any()
    else "NOVA",
    axis=1
)

# =========================================================
# ORDENAÇÃO (FILA REAL = MAIS ANTIGO PRIMEIRO)
# =========================================================
df["DATA_CAPTURA"] = pd.to_datetime(df["data_captura"], errors="coerce")
df = df.sort_values("DATA_CAPTURA")

# =========================================================
# TOPO
# =========================================================
st.markdown(f"## ⏳ Tem **{len(df)} análises** para subir")
st.divider()

# =========================================================
# CARDS
# =========================================================
cols = st.columns(3)

for i, row in df.iterrows():
    with cols[i % 3]:

        badge = "🆕 Análise nova" if row["TIPO_ANALISE"] == "NOVA" else "🔁 Reanálise"
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
