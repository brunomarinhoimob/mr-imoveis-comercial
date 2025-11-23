import streamlit as st
import requests
import pandas as pd

from utils.supremo_config import TOKEN_SUPREMO

BASE_URL_CORRETORES = "https://api.supremocrm.com.br/v1/corretores"

st.set_page_config(
    page_title="Teste API Corretores",
    page_icon="🔧",
    layout="wide",
)

st.title("🔧 Teste da API de Corretores – Supremo CRM")

st.write("Esse teste chama diretamente o endpoint `/v1/corretores` com o TOKEN_SUPREMO e mostra a resposta bruta.")

if st.button("Chamar API de corretores"):
    headers = {"Authorization": f"Bearer {TOKEN_SUPREMO}"}
    try:
        resp = requests.get(
            BASE_URL_CORRETORES,
            headers=headers,
            params={"pagina": 1},
            timeout=20,
        )
    except Exception as e:
        st.error(f"Erro de conexão com a API: {e}")
        st.stop()

    st.write("**Status code:**", resp.status_code)

    # Mostra o começo do texto bruto
    st.subheader("Resposta bruta (primeiros 1500 caracteres)")
    st.code(resp.text[:1500])

    # Tenta montar um DataFrame se vier JSON no formato esperado
    try:
        data = resp.json()
        if isinstance(data, dict) and "dados" in data:
            df = pd.DataFrame(data["dados"])
        elif isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame()

        st.subheader("Prévia dos dados em tabela (se houver):")
        if df.empty:
            st.info("Nenhum dado estruturado retornado (DataFrame vazio).")
        else:
            st.dataframe(df.head(20), use_container_width=True)
    except Exception as e:
        st.warning(f"Não consegui converter a resposta em JSON/DataFrame: {e}")
