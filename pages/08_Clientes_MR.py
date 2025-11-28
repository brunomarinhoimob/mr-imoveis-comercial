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
try:
    st.image("logo_mr.png", width=160)
except Exception:
    st.write("MR Imóveis")

st.markdown("## 🔎 Consulta de Clientes – MR Imóveis")
st.caption(
    "Pesquise o cliente para visualizar a situação atual (respeitando a regra VENDA / DESISTIU) "
    "e todo o histórico dele com o corretor."
)

# ---------------------------------------------------------
# CARREGAMENTO DOS DADOS
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def carregar_dados():
    df = carregar_dados_planilha()
    df.columns = [c.upper().strip() for c in df.columns]

    # DATA / DIA
    if "DIA" in df:
        df["DIA"] = pd.to_datetime(df["DIA"], errors="coerce")
    elif "DATA" in df:
        df["DIA"] = pd.to_datetime(df["DATA"], errors="coerce")
    else:
        df["DIA"] = pd.NaT

    # NOME
    col_nome = next(
        (c for c in ["NOME", "CLIENTE", "NOME CLIENTE", "NOME DO CLIENTE"] if c in df),
        None,
    )
    if col_nome:
        df["NOME_CLIENTE_BASE"] = (
            df[col_nome].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
        )
    else:
        df["NOME_CLIENTE_BASE"] = "NÃO INFORMADO"

    # CPF
    col_cpf = next(
        (c for c in ["CPF", "CPF CLIENTE", "CPF DO CLIENTE"] if c in df),
        None,
    )
    if col_cpf:
        df["CPF_CLIENTE_BASE"] = (
            df[col_cpf]
            .fillna("")
            .astype(str)
            .str.replace(r"\D", "", regex=True)
            .str.strip()
        )
    else:
        df["CPF_CLIENTE_BASE"] = ""

    # CORRETOR
    df["CORRETOR"] = (
        df.get("CORRETOR", "NÃO INFORMADO")
        .fillna("NÃO INFORMADO")
        .astype(str)
        .str.upper()
        .str.strip()
    )

    # CONSTRUTORA / EMPREENDIMENTO
    df["CONSTRUTORA"] = (
        df.get("CONSTRUTORA", "")
        .fillna("")
        .astype(str)
        .str.upper()
        .str.strip()
    )
    df["EMPREENDIMENTO"] = (
        df.get("EMPREENDIMENTO", "")
        .fillna("")
        .astype(str)
        .str.upper()
        .str.strip()
    )

    # STATUS / SITUAÇÃO
    situacao_col = next(
        (c for c in ["SITUAÇÃO", "SITUACAO", "STATUS", "SITUAÇÃO ATUAL"] if c in df),
        None,
    )
    if situacao_col:
        df["SITUACAO_ORIGINAL"] = (
            df[situacao_col].fillna("").astype(str).str.strip()
        )
    else:
        df["SITUACAO_ORIGINAL"] = ""

    df["STATUS_BASE"] = df["SITUACAO_ORIGINAL"].str.upper()

    # OBS / OBS2 (AGORA SEM NAN)
    df["OBS"] = (
        df.get("OBSERVAÇÕES", "")
        .fillna("")
        .astype(str)
        .str.strip()
    )
    df["OBS2"] = (
        df.get("OBSERVAÇÕES 2", "")
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # CHAVE CLIENTE
    df["CHAVE"] = df["NOME_CLIENTE_BASE"] + "|" + df["CPF_CLIENTE_BASE"]

    return df


df = carregar_dados()

# ---------------------------------------------------------
# BUSCA
# ---------------------------------------------------------
st.sidebar.title("Busca Cliente")

modo_busca = st.sidebar.radio("Buscar por:", ["Nome", "CPF"])
termo = st.sidebar.text_input("Digite para buscar")

def obter_status_atual(df_cli: pd.DataFrame) -> pd.Series:
    """
    Regra:
    - Considera apenas o trecho após o último DESISTIU (se existir);
    - Dentro desse trecho, se tiver VENDA GERADA / VENDA INFORMADA, pega a última venda;
    - Se não tiver venda, pega a última linha do trecho.
    """
    df_cli = df_cli.sort_values("DIA").copy()

    # Último DESISTIU
    mask_desistiu = df_cli["STATUS_BASE"].str.contains("DESIST", na=False)
    if mask_desistiu.any():
        idx_last_reset = df_cli[mask_desistiu].index[-1]
        df_seg = df_cli.loc[idx_last_reset:]
    else:
        df_seg = df_cli

    # Verifica vendas dentro do ciclo atual
    mask_venda = df_seg["STATUS_BASE"].isin(["VENDA GERADA", "VENDA INFORMADA"])
    if mask_venda.any():
        return df_seg[mask_venda].iloc[-1]
    else:
        return df_seg.iloc[-1]


if termo.strip():
    termo_input = termo.strip().upper()

    if modo_busca == "Nome":
        mask = df["NOME_CLIENTE_BASE"].str.contains(termo_input, na=False)
    else:
        cpf_num = "".join(c for c in termo if c.isdigit())
        mask = df["CPF_CLIENTE_BASE"].str.contains(cpf_num, na=False)

    resultado = df[mask].copy()

    if resultado.empty:
        st.warning("Cliente não encontrado na base.")
    else:
        # Agrupa por cliente + corretor (história por corretor)
        for (chave, corr), grupo in resultado.groupby(["CHAVE", "CORRETOR"]):
            grupo = grupo.sort_values("DIA").copy()
            ultima = obter_status_atual(grupo)

            nome_cli = ultima["NOME_CLIENTE_BASE"]
            cpf_cli = ultima["CPF_CLIENTE_BASE"]
            data_ult = (
                ultima["DIA"].strftime("%d/%m/%Y")
                if pd.notna(ultima["DIA"])
                else ""
            )
            situacao_atual = ultima["SITUACAO_ORIGINAL"] or "NÃO INFORMADO"
            corretor = ultima["CORRETOR"]
            construtora = ultima.get("CONSTRUTORA", "") or "NÃO INFORMADO"
            empreendimento = ultima.get("EMPREENDIMENTO", "") or "NÃO INFORMADO"

            # OBS: sempre limpar possíveis 'nan'
            obs2 = (ultima.get("OBS2", "") or "").strip()
            obs1 = (ultima.get("OBS", "") or "").strip()
            ultima_obs = obs2 if obs2 else obs1

            st.markdown("---")
            st.markdown(f"### 👤 {nome_cli}")
            st.write(f"**CPF:** `{'NÃO INFORMADO' if not cpf_cli else cpf_cli}`")
            st.write(f"**Última movimentação:** `{data_ult}`")
            st.write(f"**Situação atual:** `{situacao_atual}`")
            st.write(f"**Corretor responsável:** `{corretor}`")
            st.write(f"**Construtora:** `{construtora}`")
            st.write(f"**Empreendimento:** `{empreendimento}`")

            if ultima_obs:
                st.markdown("**Última observação:**")
                st.info(ultima_obs)

            # ---------------- LINHA DO TEMPO ----------------
            st.markdown("#### 📜 Histórico do cliente com este corretor")

            df_hist = grupo[["DIA", "SITUACAO_ORIGINAL", "OBS", "OBS2"]].copy()

            df_hist["DIA"] = df_hist["DIA"].dt.strftime("%d/%m/%Y")
            # Limpa textos 'nan' se ainda tiver restado algo
            for col in ["OBS", "OBS2"]:
                df_hist[col] = (
                    df_hist[col]
                    .fillna("")
                    .astype(str)
                    .replace("nan", "")
                    .str.strip()
                )

            df_hist = df_hist.rename(
                columns={
                    "DIA": "Data",
                    "SITUACAO_ORIGINAL": "Situação",
                    "OBS": "Obs",
                    "OBS2": "Obs 2",
                }
            )

            st.dataframe(
                df_hist,
                use_container_width=True,
                hide_index=True,
            )

else:
    st.info("Digite o nome ou CPF na barra lateral para consultar um cliente.")
