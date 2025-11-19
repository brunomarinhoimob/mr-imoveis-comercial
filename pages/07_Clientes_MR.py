import streamlit as st
import pandas as pd
import numpy as np
from datetime import date

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Clientes MR – MR Imóveis",
    page_icon="🧑‍💼",
    layout="wide",
)

st.title("🧑‍💼 Página de Clientes – MR Imóveis")
st.caption(
    "Busque clientes pelo nome (parcial) ou CPF e veja o histórico de análises, "
    "aprovações, vendas e a situação atual."
)

# ---------------------------------------------------------
# FUNÇÃO AUXILIAR PARA LIMPAR DATA
# ---------------------------------------------------------
def limpar_para_data(serie):
    dt = pd.to_datetime(serie, dayfirst=True, errors="coerce")
    return dt.dt.date

# ---------------------------------------------------------
# CONFIG: LINK DA PLANILHA (MESMO DOS OUTROS APPS)
# ---------------------------------------------------------
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID_ANALISES = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ANALISES}"

# ---------------------------------------------------------
# CARREGAR E PREPARAR DADOS
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def carregar_dados():
    df = pd.read_csv(CSV_URL)

    # Padroniza nomes de colunas
    df.columns = [c.strip().upper() for c in df.columns]

    # DATA / DIA
    if "DATA" in df.columns:
        df["DIA"] = limpar_para_data(df["DATA"])
    elif "DIA" in df.columns:
        df["DIA"] = limpar_para_data(df["DIA"])
    else:
        df["DIA"] = pd.NaT

    # EQUIPE / CORRETOR
    for col in ["EQUIPE", "CORRETOR"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .fillna("NÃO INFORMADO")
                .astype(str)
                .str.upper()
                .str.strip()
            )
        else:
            df[col] = "NÃO INFORMADO"

    # STATUS BASE (mesma lógica das outras páginas)
    possiveis_cols_situacao = [
        "SITUAÇÃO",
        "SITUAÇÃO ATUAL",
        "STATUS",
        "SITUACAO",
        "SITUACAO ATUAL",
    ]
    col_situacao = None
    for c in possiveis_cols_situacao:
        if c in df.columns:
            col_situacao = c
            break

    df["STATUS_BASE"] = ""
    if col_situacao:
        status = df[col_situacao].fillna("").astype(str).str.upper()
        df.loc[status.str.contains("EM ANÁLISE"), "STATUS_BASE"] = "EM ANÁLISE"
        df.loc[status.str.contains("REANÁLISE"), "STATUS_BASE"] = "REANÁLISE"
        df.loc[status.str.contains("APROV"), "STATUS_BASE"] = "APROVADO"
        df.loc[status.str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
        df.loc[status.str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA GERADA"
        df.loc[status.str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA INFORMADA"

    # VGV (via OBSERVAÇÕES) – em REAL
    if "OBSERVAÇÕES" in df.columns:
        df["VGV"] = pd.to_numeric(df["OBSERVAÇÕES"], errors="coerce").fillna(0.0)
    else:
        df["VGV"] = 0.0

    # -------------------------------------------------
    # TENTA IDENTIFICAR COLUNA DE NOME E CPF DO CLIENTE
    # -------------------------------------------------
    possiveis_nome = ["NOME", "CLIENTE", "NOME CLIENTE", "NOME DO CLIENTE"]
    possiveis_cpf = ["CPF", "CPF CLIENTE", "CPF DO CLIENTE"]

    col_nome = None
    for c in possiveis_nome:
        if c in df.columns:
            col_nome = c
            break

    col_cpf = None
    for c in possiveis_cpf:
        if c in df.columns:
            col_cpf = c
            break

    # Se não tiver nome/CPF na planilha, cria colunas vazias
    if col_nome is None:
        df["NOME_CLIENTE_BASE"] = "NÃO INFORMADO"
    else:
        df["NOME_CLIENTE_BASE"] = (
            df[col_nome].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
        )

    if col_cpf is None:
        df["CPF_CLIENTE_BASE"] = ""
    else:
        # deixa apenas dígitos para facilitar busca
        df["CPF_CLIENTE_BASE"] = (
            df[col_cpf]
            .fillna("")
            .astype(str)
            .str.replace(r"\D", "", regex=True)
        )

    return df


df = carregar_dados()

if df.empty:
    st.error("Não foi possível carregar dados da planilha. Verifique o link.")
    st.stop()

# ---------------------------------------------------------
# BARRA LATERAL – BUSCA
# ---------------------------------------------------------
st.sidebar.title("Busca de clientes 🔎")

tipo_busca = st.sidebar.radio(
    "Buscar por:",
    ("Nome (parcial)", "CPF"),
    horizontal=False,
)

termo = st.sidebar.text_input(
    "Digite o nome ou CPF do cliente",
    placeholder="Ex: MARIA / 12345678901",
)

st.sidebar.caption(
    "• Nome: pode digitar só uma parte (ex: 'SILVA')\n"
    "• CPF: digite só números (não precisa de ponto ou traço)"
)

# ---------------------------------------------------------
# FILTRO POR BUSCA
# ---------------------------------------------------------
df_resultado = pd.DataFrame()

if termo.strip():
    termo_limpo = termo.strip().upper()

    if tipo_busca.startswith("Nome"):
        # busca parcial no nome
        df_resultado = df[
            df["NOME_CLIENTE_BASE"].str.contains(termo_limpo, na=False)
        ].copy()
    else:
        # busca por CPF – deixa só dígitos
        termo_cpf = "".join(ch for ch in termo if ch.isdigit())
        df_resultado = df[
            df["CPF_CLIENTE_BASE"].str.contains(termo_cpf, na=False)
        ].copy()

# ---------------------------------------------------------
# EXIBIÇÃO DOS RESULTADOS
# ---------------------------------------------------------
if not termo.strip():
    st.info("Digite um nome ou CPF na lateral para iniciar a busca.")
elif df_resultado.empty:
    st.warning("Nenhum cliente encontrado com esse critério de busca.")
else:
    # Agrupa por cliente (nome + CPF) para resumir histórico
    df_resultado["CHAVE_CLIENTE"] = (
        df_resultado["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO")
        + " | "
        + df_resultado["CPF_CLIENTE_BASE"].fillna("")
    )

    # Funções auxiliares
    def conta_analises(s):
        return s.isin(["EM ANÁLISE", "REANÁLISE"]).sum()

    def conta_aprovacoes(s):
        return (s == "APROVADO").sum()

    def conta_vendas(s):
        return s.isin(["VENDA GERADA", "VENDA INFORMADA"]).sum()

    # Resumo por cliente
    resumo = (
        df_resultado.groupby("CHAVE_CLIENTE")
        .agg(
            NOME=("NOME_CLIENTE_BASE", "first"),
            CPF=("CPF_CLIENTE_BASE", "first"),
            ANALISES=("STATUS_BASE", conta_analises),
            APROVACOES=("STATUS_BASE", conta_aprovacoes),
            VENDAS=("STATUS_BASE", conta_vendas),
            VGV=("VGV", "sum"),
            ULT_STATUS=("STATUS_BASE", lambda x: x.iloc[-1] if len(x) > 0 else ""),
            ULT_DATA=("DIA", lambda x: x.max()),
        )
        .reset_index(drop=True)
    )

    st.markdown(
        f"### 🔎 Resultado da busca – {len(resumo)} cliente(s) encontrado(s)"
    )

    # Mostra primeiro uma tabela simples (para visão geral)
    st.markdown("#### 📋 Visão geral")
    st.dataframe(
        resumo[["NOME", "CPF", "ULT_STATUS", "ULT_DATA", "ANALISES", "APROVACOES", "VENDAS", "VGV"]]
        .sort_values(["VENDAS", "VGV"], ascending=False)
        .style.format(
            {
                "VGV": "R$ {:,.2f}".format,
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("#### 💳 Detalhes por cliente (cards)")

    # Cards para cada cliente
    for _, row in resumo.sort_values(["VENDAS", "VGV"], ascending=False).iterrows():
        with st.container():
            st.markdown("---")
            st.markdown(f"##### 👤 {row['NOME']}")
            col_top1, col_top2 = st.columns(2)
            with col_top1:
                cpf_fmt = row["CPF"]
                if cpf_fmt:
                    st.write(f"**CPF:** `{cpf_fmt}`")
                else:
                    st.write("**CPF:** não informado")
                st.write(f"**Situação atual:** `{row['ULT_STATUS'] or 'NÃO INFORMADO'}`")
            with col_top2:
                if pd.notna(row["ULT_DATA"]):
                    st.write(f"**Última movimentação:** {row['ULT_DATA'].strftime('%d/%m/%Y')}")
                else:
                    st.write("**Última movimentação:** não informada")

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Análises (EM + RE)", int(row["ANALISES"]))
            with c2:
                st.metric("Aprovações", int(row["APROVACOES"]))
            with c3:
                st.metric("Vendas", int(row["VENDAS"]))
            with c4:
                st.metric(
                    "VGV total",
                    f"R$ {row['VGV']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                )
