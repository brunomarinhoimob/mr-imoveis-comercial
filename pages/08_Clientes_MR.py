import streamlit as st
import pandas as pd
from datetime import date

from app_dashboard import carregar_dados_planilha

st.set_page_config(
    page_title="Clientes MR",
    page_icon="🧑‍💼",
    layout="wide",
)

# LOGO
st.image("logo_mr.png", width=160)

st.markdown("## 🔎 Consulta de Clientes – MR Imóveis")
st.caption("Pesquise o cliente para visualizar a situação atual e todo o histórico com o corretor.")

# -----------------------------
# CARREGAMENTO DOS DADOS
# -----------------------------
@st.cache_data(ttl=60)
def carregar_dados():
    df = carregar_dados_planilha()
    df.columns = [c.upper().strip() for c in df.columns]

    # DATA
    if "DIA" in df:
        df["DIA"] = pd.to_datetime(df["DIA"], errors="coerce")
    elif "DATA" in df:
        df["DIA"] = pd.to_datetime(df["DATA"], errors="coerce")
    else:
        df["DIA"] = pd.NaT

    # NOME
    for col in ["NOME", "CLIENTE", "NOME CLIENTE"]:
        if col in df:
            df["NOME_CLIENTE_BASE"] = df[col].astype(str).str.upper().str.strip()
            break
    else:
        df["NOME_CLIENTE_BASE"] = "NÃO INFORMADO"

    # CPF
    for col in ["CPF", "CPF CLIENTE"]:
        if col in df:
            df["CPF_CLIENTE_BASE"] = df[col].astype(str).str.replace(r"\D", "", regex=True)
            break
    else:
        df["CPF_CLIENTE_BASE"] = ""

    # CORRETOR
    df["CORRETOR"] = df.get("CORRETOR", "NÃO INFORMADO").fillna("NÃO INFORMADO").astype(str).str.upper()

    # CONSTRUTORA / EMPREENDIMENTO
    df["CONSTRUTORA"] = df.get("CONSTRUTORA", "").astype(str).str.upper()
    df["EMPREENDIMENTO"] = df.get("EMPREENDIMENTO", "").astype(str).str.upper()

    # STATUS
    situacao_col = next((c for c in ["SITUAÇÃO", "STATUS", "SITUACAO"] if c in df), None)
    df["SITUACAO_ORIGINAL"] = df[situacao_col].astype(str).str.strip() if situacao_col else ""
    df["STATUS_BASE"] = df["SITUACAO_ORIGINAL"].str.upper()

    # OBS
    df["OBS"] = df.get("OBSERVAÇÕES", "").astype(str).str.strip()
    df["OBS2"] = df.get("OBSERVAÇÕES 2", "").astype(str).str.strip()

    # CHAVE
    df["CHAVE"] = df["NOME_CLIENTE_BASE"] + "|" + df["CPF_CLIENTE_BASE"]

    return df


df = carregar_dados()

# -----------------------------
# BUSCA
# -----------------------------
st.sidebar.title("Busca Cliente")

modalidade = st.sidebar.radio("Buscar por:", ["Nome", "CPF"])
termo = st.sidebar.text_input("Digite para buscar")

def obter_status_atual(df_cli):
    df_cli = df_cli.sort_values("DIA")

    desistiu = df_cli[df_cli["STATUS_BASE"].str.contains("DESIST")]
    if not desistiu.empty:
        df_cli = df_cli.loc[desistiu.index[-1]:]

    vendas = df_cli[df_cli["STATUS_BASE"].isin(["VENDA GERADA", "VENDA INFORMADA"])]
    if not vendas.empty:
        return vendas.iloc[-1]
    else:
        return df_cli.iloc[-1]


if termo.strip():
    termo = termo.upper().strip()

    if modalidade == "Nome":
        filtro = df["NOME_CLIENTE_BASE"].str.contains(termo, na=False)
    else:
        filtro = df["CPF_CLIENTE_BASE"].str.contains("".join(c for c in termo if c.isdigit()), na=False)

    resultado = df[filtro]

    if resultado.empty:
        st.warning("Cliente não encontrado.")
    else:
        for (chave, corretor), grupo in resultado.groupby(["CHAVE", "CORRETOR"]):
            ultima = obter_status_atual(grupo)

            st.markdown("---")
            st.markdown(f"### 👤 {ultima['NOME_CLIENTE_BASE']}")
            st.write(f"**CPF:** `{ultima['CPF_CLIENTE_BASE']}`")
            st.write(f"**Última movimentação:** `{ultima['DIA'].strftime('%d/%m/%Y') if pd.notna(ultima['DIA']) else ''}`")
            st.write(f"**Situação atual:** `{ultima['SITUACAO_ORIGINAL']}`")
            st.write(f"**Corretor responsável:** `{ultima['CORRETOR']}`")
            st.write(f"**Construtora:** `{ultima.get('CONSTRUTORA','')}`")
            st.write(f"**Empreendimento:** `{ultima.get('EMPREENDIMENTO','')}`")

            obs = ultima["OBS2"] or ultima["OBS"]
            if obs:
                st.markdown("**Última observação:**")
                st.info(obs)

            # HISTÓRICO
            st.markdown("#### 📜 Histórico do cliente com este corretor")
            st.dataframe(
                grupo.sort_values("DIA")[["DIA","SITUACAO_ORIGINAL","OBS","OBS2"]],
                use_container_width=True,
                hide_index=True
            )

else:
    st.info("Digite o nome ou CPF para consultar um cliente.")
