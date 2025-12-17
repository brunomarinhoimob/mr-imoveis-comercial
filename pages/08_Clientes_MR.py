import streamlit as st
import pandas as pd

# =========================================================
# BLOQUEIO SEM LOGIN
# =========================================================
if "logado" not in st.session_state or not st.session_state.logado:
    st.warning("🔒 Acesso restrito. Faça login para continuar.")
    st.stop()

from app_dashboard import carregar_dados_planilha

st.set_page_config(
    page_title="Clientes MR",
    page_icon="👥",
    layout="wide"
)

# =========================================================
# CONTEXTO DO USUÁRIO
# =========================================================
perfil = st.session_state.get("perfil")
nome_corretor_logado = (
    st.session_state.get("nome_usuario", "")
    .upper()
    .strip()
)

# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================
def badge_status(texto):
    texto = (texto or "").upper()
    cores = {
        "EM ANÁLISE": "#2563eb",
        "REANÁLISE": "#9333ea",
        "APROVADO": "#16a34a",
        "APROVADO BACEN": "#f97316",
        "REPROVADO": "#dc2626",
        "VENDA GERADA": "#15803d",
        "VENDA INFORMADA": "#166534",
        "DESISTIU": "#6b7280",
    }
    cor = cores.get(texto, "#374151")
    return f"<span style='background:{cor};color:white;padding:4px 10px;border-radius:12px;font-size:0.85rem;font-weight:600'>{texto}</span>"

def obter_status_atual(grupo):
    grupo = grupo.sort_values("DIA").copy()
    desist = grupo["SITUACAO_ORIGINAL"].str.contains("DESIST", na=False)
    if desist.any():
        grupo = grupo.loc[grupo[desist].index[-1]:]
    vendas = grupo[grupo["STATUS_BASE"].isin(["VENDA GERADA", "VENDA INFORMADA"])]
    if not vendas.empty:
        return vendas.iloc[-1]
    return grupo.iloc[-1]

# =========================================================
# CARREGAR BASE
# =========================================================
@st.cache_data(ttl=60)
def carregar_base():
    df = carregar_dados_planilha()
    df.columns = df.columns.str.upper().str.strip()

    if "DIA" in df:
        df["DIA"] = pd.to_datetime(df["DIA"], errors="coerce")
    elif "DATA" in df:
        df["DIA"] = pd.to_datetime(df["DATA"], errors="coerce")
    else:
        df["DIA"] = pd.NaT

    df["NOME_CLIENTE_BASE"] = df.get("NOME_CLIENTE_BASE", df.get("NOME", "")).fillna("").str.upper()
    df["CPF_CLIENTE_BASE"] = df.get("CPF_CLIENTE_BASE", df.get("CPF", "")).fillna("").astype(str).str.replace(r"\D", "", regex=True)

    df["CORRETOR"] = df.get("CORRETOR", "").fillna("").str.upper().str.strip()
    df["EQUIPE"] = df.get("EQUIPE", "").fillna("").str.upper()
    df["CONSTRUTORA"] = df.get("CONSTRUTORA", "").fillna("").str.upper()
    df["EMPREENDIMENTO"] = df.get("EMPREENDIMENTO", "").fillna("").str.upper()

    col_sit = next((c for c in ["SITUACAO", "SITUAÇÃO", "STATUS"] if c in df), None)
    df["SITUACAO_ORIGINAL"] = df[col_sit].fillna("").astype(str) if col_sit else ""
    df["STATUS_BASE"] = df["SITUACAO_ORIGINAL"].str.upper()

    df["CHAVE"] = df["NOME_CLIENTE_BASE"] + "|" + df["CPF_CLIENTE_BASE"]
    return df

df = carregar_base()

# =========================================================
# BUSCA
# =========================================================
st.markdown("## 👥 Consulta de Clientes – MR")
col1, col2 = st.columns([1, 2])

with col1:
    cpf_busca = st.text_input("CPF do cliente")

with col2:
    nome_busca = st.text_input("Nome do cliente")

if not cpf_busca and not nome_busca:
    st.info("Informe CPF ou nome para buscar.")
    st.stop()

mask = pd.Series(False, index=df.index)

if cpf_busca:
    cpf = cpf_busca.replace(".", "").replace("-", "").strip()
    mask = df["CPF_CLIENTE_BASE"] == cpf

if nome_busca:
    nome = nome_busca.upper().strip()
    mask = mask | df["NOME_CLIENTE_BASE"].str.contains(nome, na=False)

resultado = df[mask].copy()

# =========================================================
# VALIDAÇÃO E FILTRO DE POSSE (REGRA FORTE)
# =========================================================
if perfil == "corretor":

    resultado = resultado[
        resultado["CORRETOR"].str.upper().str.strip()
        == nome_corretor_logado
    ]

    if resultado.empty:
        st.error("🚫 Cliente não pertence à sua carteira ou não possui análise com você.")
        st.stop()

if perfil == "corretor":
    pertence = resultado["CORRETOR"].eq(nome_corretor_logado).any()
    if not pertence:
        st.error("🚫 Cliente não pertence à sua carteira.")
        st.stop()

# =========================================================
# EXIBIÇÃO
# =========================================================
for (chave, corretor), grupo in resultado.groupby(["CHAVE", "CORRETOR"]):
    ultima = obter_status_atual(grupo)

    st.markdown("---")
    st.markdown(f"### 👤 {ultima['NOME_CLIENTE_BASE']}")
    st.write(f"**CPF:** `{ultima['CPF_CLIENTE_BASE'] or 'NÃO INFORMADO'}`")

    if pd.notna(ultima["DIA"]):
        st.write(f"**Última movimentação:** {ultima['DIA'].strftime('%d/%m/%Y')}")

    st.markdown(f"**Situação atual:** {badge_status(ultima['SITUACAO_ORIGINAL'])}", unsafe_allow_html=True)
    st.write(f"**Corretor responsável:** `{ultima['CORRETOR']}`")
    st.write(f"**Construtora:** `{ultima['CONSTRUTORA'] or 'NÃO INFORMADO'}`")
    st.write(f"**Empreendimento:** `{ultima['EMPREENDIMENTO'] or 'NÃO INFORMADO'}`")

    obs = (ultima.get("OBS2") or ultima.get("OBS") or "").strip()
    if obs:
        st.info(obs)

    cols_hist = ["DIA", "SITUACAO_ORIGINAL"]
    if "OBS" in grupo.columns:
        cols_hist.append("OBS")
    if "OBS2" in grupo.columns:
        cols_hist.append("OBS2")

    hist = grupo[cols_hist].copy()
    hist["DIA"] = hist["DIA"].dt.strftime("%d/%m/%Y")

    st.dataframe(hist, use_container_width=True, hide_index=True)
