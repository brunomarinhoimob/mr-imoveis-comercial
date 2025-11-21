import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# CLIENTES EM ANÁLISE / REANÁLISE
# ---------------------------------------------------------

st.markdown("## 📝 Clientes em Análise / Reanálise")

# Logo MR
col_logo, col_titulo = st.columns([1, 4])
with col_logo:
    try:
        st.image("logo_mr.png", use_column_width=True)
    except Exception:
        st.write(" ")

with col_titulo:
    st.markdown(
        """
        Aqui você acompanha apenas os clientes **cujo status atual** na planilha
        está como **EM ANÁLISE** ou **REANÁLISE**, independente de quantas linhas
        anteriores eles já tiveram (aprovado, venda, etc.).
        """
    )

# ---------------------------------------------------------
# 🔹 CARREGA O DATAFRAME df
#    👉 COPIE DA SUA OUTRA PÁGINA O MESMO JEITO QUE VOCÊ CARREGA A PLANILHA
# ---------------------------------------------------------
# Exemplo genérico (APAGUE/ADAPTE para o que você realmente usa):
# from utils.data_loader import load_base
# df = load_base()

df = st.session_state.get("df", None)  # se você já salva o df no session_state no app principal

if df is None or df.empty:
    st.info("A base ainda está vazia ou o df não foi carregado no session_state.")
    st.stop()

# ---------------------------------------------------------
# LÓGICA DOS CLIENTES EM ANÁLISE
# ---------------------------------------------------------

# Descobre a coluna de cliente
if "CLIENTE" in df.columns:
    col_cliente = "CLIENTE"
elif "NOME_CLIENTE" in df.columns:
    col_cliente = "NOME_CLIENTE"
else:
    st.error(
        "Não encontrei uma coluna de cliente (CLIENTE ou NOME_CLIENTE). "
        "Ajuste o código para usar o nome correto da coluna."
    )
    st.stop()

if "STATUS_BASE" not in df.columns:
    st.error("Não encontrei a coluna STATUS_BASE na base. Ajuste o nome da coluna de status.")
    st.stop()

if "DIA" not in df.columns:
    st.error("Não encontrei a coluna DIA (data do evento). Ajuste o nome da coluna de data.")
    st.stop()

# Converte a coluna de data
df["DIA"] = pd.to_datetime(df["DIA"], errors="coerce")

# Remove registros sem data (se houver)
df_valid = df.dropna(subset=["DIA"]).copy()

if df_valid.empty:
    st.info("Não foi possível identificar datas válidas nos registros.")
    st.stop()

# Ordena por cliente + data (da mais antiga para a mais recente)
df_valid = df_valid.sort_values(by=[col_cliente, "DIA"])

# Pega apenas o ÚLTIMO registro de cada cliente (status atual)
df_status_atual = df_valid.drop_duplicates(subset=[col_cliente], keep="last").copy()

# Filtra clientes que atualmente estão EM ANÁLISE ou REANÁLISE
status_em_analise = ["EM ANÁLISE", "REANÁLISE"]
df_em_analise_atual = df_status_atual[
    df_status_atual["STATUS_BASE"].isin(status_em_analise)
].copy()

if df_em_analise_atual.empty:
    st.success("No momento, nenhum cliente está com status EM ANÁLISE ou REANÁLISE. 👏")
    st.stop()

# -----------------------------
# FILTRO POR EQUIPE
# -----------------------------
if "EQUIPE" in df_em_analise_atual.columns:
    equipes = (
        df_em_analise_atual["EQUIPE"]
        .dropna()
        .astype(str)
        .sort_values()
        .unique()
        .tolist()
    )

    equipe_selecionada = st.selectbox(
        "Filtrar por equipe:",
        options=["Todas"] + equipes,
        index=0
    )

    if equipe_selecionada != "Todas":
        df_filtrado = df_em_analise_atual[
            df_em_analise_atual["EQUIPE"] == equipe_selecionada
        ].copy()
    else:
        df_filtrado = df_em_analise_atual.copy()
else:
    st.warning(
        "Coluna 'EQUIPE' não encontrada na base. "
        "Os filtros por equipe não serão exibidos."
    )
    df_filtrado = df_em_analise_atual.copy()

if df_filtrado.empty:
    st.info("Não há clientes em análise para os filtros selecionados.")
    st.stop()

# -----------------------------
# KPIs / MÉTRICAS
# -----------------------------
total_em_analise = len(df_filtrado)
qtd_em_analise = (df_filtrado["STATUS_BASE"] == "EM ANÁLISE").sum()
qtd_reanalise = (df_filtrado["STATUS_BASE"] == "REANÁLISE").sum()

col1, col2, col3 = st.columns(3)
col1.metric("Total em Análise (atual)", total_em_analise)
col2.metric("Em Análise", qtd_em_analise)
col3.metric("Reanálise", qtd_reanalise)

st.markdown("---")

# -----------------------------
# TABELA DETALHADA
# -----------------------------
colunas_preferidas = [
    col_cliente,
    "TELEFONE",
    "EQUIPE",
    "CORRETOR",
    "EMPREENDIMENTO",
    "STATUS_BASE",
    "DIA",
]
colunas_existentes = [c for c in colunas_preferidas if c in df_filtrado.columns]

st.markdown("### 📋 Lista de clientes em análise (status atual)")
st.dataframe(
    df_filtrado[colunas_existentes].sort_values("DIA", ascending=False),
    use_container_width=True,
)

# -----------------------------
# RESUMO POR EQUIPE
# -----------------------------
if "EQUIPE" in df_filtrado.columns:
    st.markdown("### 👥 Quantidade de clientes em análise por equipe")

    resumo_equipe = (
        df_filtrado.groupby("EQUIPE")[col_cliente]
        .nunique()
        .reset_index(name="Qtde Clientes")
        .sort_values("Qtde Clientes", ascending=False)
    )

    st.dataframe(resumo_equipe, use_container_width=True)
