# =========================================================
# PRÉ-CADASTRO – ANÁLISES PENDENTES (ÚLTIMOS 7 DIAS)
# REGRA: CLIENTE + CORRETOR
# <= 60 DIAS  -> REANÁLISE
# >  60 DIAS  -> NOVA ANÁLISE
# VISUAL: GLOW VERDE (NOVA) | GLOW ÂMBAR (REANÁLISE)
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
# AUTO REFRESH (30s)
# =========================================================
st_autorefresh(interval=30 * 1000, key="auto_refresh_pre_cadastro_18")

# =========================================================
# CONFIGURAÇÕES
# =========================================================
API_URL = "https://api.supremocrm.com.br/v1/leads"
HEADERS = {"Authorization": f"Bearer {TOKEN_SUPREMO}"}

SITUACAO_ALVO = "ANALISE PENDENTE"
DIAS_JANELA_CRM = 7
LIMITE_REANALISE = 60

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
# CARGA CRM (ÚLTIMOS 7 DIAS)
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
# LOAD DADOS
# =========================================================
df_leads = carregar_leads_crm()
df_plan = carregar_dados_planilha()

if df_leads.empty:
    st.success("🎉 Nenhuma análise pendente no momento.")
    st.stop()

# =========================================================
# NORMALIZA CHAVES
# =========================================================
df_leads["CLIENTE_KEY"] = df_leads["nome_pessoa"].apply(normalizar)
df_leads["CORRETOR_KEY"] = df_leads["nome_corretor"].apply(normalizar)

df_plan["CLIENTE_KEY"] = df_plan["CLIENTE"].apply(normalizar)
df_plan["CORRETOR_KEY"] = df_plan["CORRETOR"].apply(normalizar)

# DATA DA ANÁLISE (COLUNA A – BR)
df_plan["DATA"] = df_plan["DATA"].astype(str).str.strip()
dt1 = pd.to_datetime(df_plan["DATA"], errors="coerce", dayfirst=True)
dt2 = pd.to_datetime(df_plan["DATA"], errors="coerce")
df_plan["DATA"] = dt1.fillna(dt2)

# =========================================================
# FILTRO – ANÁLISE PENDENTE
# =========================================================
df = df_leads[
    df_leads["nome_situacao"].astype(str).str.upper() == SITUACAO_ALVO
].copy()

# =========================================================
# CLASSIFICAÇÃO NOVA x REANÁLISE
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
# ORDENAÇÃO FIFO
# =========================================================
df["DATA_CAPTURA"] = pd.to_datetime(df["data_captura"], errors="coerce")
df = df.sort_values("DATA_CAPTURA")

# =========================================================
# TOPO
# =========================================================
st.markdown(f"## ⏳ Tem **{len(df)} análises** para subir")
st.divider()

# =========================================================
# CARDS COM GLOW
# =========================================================
cols = st.columns(3)

for i, row in df.iterrows():
    with cols[i % 3]:

        is_nova = row["TIPO_ANALISE"] == "NOVA"
        glow = "0 0 22px rgba(34,197,94,0.45)" if is_nova else "0 0 22px rgba(245,158,11,0.45)"
        border = "#22c55e" if is_nova else "#f59e0b"
        badge = "🆕 NOVA ANÁLISE" if is_nova else "🔁 REANÁLISE"

        obs = row.get("anotacoes") or "Sem observações"
        obs = obs[:200] + "..." if len(obs) > 200 else obs

        data_cap = "-"
        if pd.notna(row.get("DATA_CAPTURA")):
            data_cap = row["DATA_CAPTURA"].strftime("%d/%m/%Y")

        st.markdown(
    f"""
    <div style="
        border: 2px solid {border};
        border-radius: 18px;
        padding: 18px;
        margin-bottom: 24px;
        background: linear-gradient(180deg, #0f172a 0%, #020617 100%);
        box-shadow: {glow};
    ">

        <div style="display:flex; justify-content:space-between; align-items:center;">
            <h4 style="margin:0; font-size:18px; font-weight:600; color:#ffffff;">
                {row['nome_pessoa']}
            </h4>
            <span style="
                font-size:12px;
                padding:5px 12px;
                border-radius:999px;
                background:{border};
                color:#020617;
                font-weight:700;
            ">
                {badge}
            </span>
        </div>

        <div style="margin-top:14px; font-size:14px; line-height:1.7; color:#e5e7eb;">
            📧 Email: {row.get('email_pessoa','-')}<br>
            📞 Telefone: {row.get('telefone_pessoa','-')}<br>
            👤 Corretor: {row.get('nome_corretor','-')}<br>
            🗓️ Captura: {data_cap}
        </div>

        <div style="
            margin-top:14px;
            padding:10px 12px;
            background:#020617;
            border-radius:12px;
            font-size:13px;
            color:#cbd5f5;
        ">
            📝 {obs}
        </div>

        <div style="
            margin-top:14px;
            padding-top:10px;
            border-top:1px solid #1e293b;
            font-size:13px;
            color:#93c5fd;
            font-weight:600;
        ">
            📌 Situação: {row.get('nome_situacao','-')}
        </div>

    </div>
    """,
    unsafe_allow_html=True
)

