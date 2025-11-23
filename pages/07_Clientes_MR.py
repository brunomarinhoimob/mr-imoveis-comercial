import streamlit as st
import pandas as pd
import numpy as np
import re
from datetime import date

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Clientes MR – MR Imóveis",
    page_icon="🧑‍💼",
    layout="wide",
)

# ---------------------------------------------------------
# LOGO MR IMÓVEIS
# ---------------------------------------------------------
LOGO_PATH = "logo_mr.png"

col_titulo, col_logo = st.columns([3, 1])
with col_titulo:
    st.title("🧑‍💼 Clientes MR – Consulta detalhada por cliente")
with col_logo:
    try:
        st.image(LOGO_PATH, use_column_width=True)
    except Exception:
        pass

st.markdown(
    "Busque um cliente pelo **nome** ou **CPF** e veja o histórico completo de análises, "
    "aprovações e vendas. Sempre consideramos a **última ação registrada** para o status "
    "atual do cliente, e **VENDA GERADA anula VENDA INFORMADA** na contagem de vendas/VGV."
)

# ---------------------------------------------------------
# PLANILHA BASE
# ---------------------------------------------------------
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID_ANALISES = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ANALISES}"


# ---------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------
def limpar_para_data(serie):
    dt = pd.to_datetime(serie, dayfirst=True, errors="coerce")
    return dt.dt.date


def normalizar_nome(nome: str) -> str:
    if pd.isna(nome):
        return ""
    s = str(nome).upper().strip()
    s = re.sub(r"\s+", " ", s)  # remove espaços duplicados
    return s


def limpar_cpf(cpf: str) -> str:
    if pd.isna(cpf):
        return ""
    return re.sub(r"\D", "", str(cpf))


# ---------------------------------------------------------
# CARREGAR DADOS
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def carregar_dados():
    df = pd.read_csv(CSV_URL)

    # Padroniza colunas
    df.columns = [c.strip().upper() for c in df.columns]

    # DATA / DIA
    if "DATA" in df.columns:
        df["DIA"] = limpar_para_data(df["DATA"])
    elif "DIA" in df.columns:
        df["DIA"] = limpar_para_data(df["DIA"])
    else:
        df["DIA"] = pd.NaT

    df["DT_BASE"] = pd.to_datetime(df["DIA"], errors="coerce")

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

    # NOME / CPF BASE
    possiveis_nome = ["NOME", "CLIENTE", "NOME CLIENTE", "NOME DO CLIENTE"]
    possiveis_cpf = ["CPF", "CPF CLIENTE", "CPF DO CLIENTE"]

    col_nome = next((c for c in possiveis_nome if c in df.columns), None)
    col_cpf = next((c for c in possiveis_cpf if c in df.columns), None)

    if col_nome is None:
        df["NOME_CLIENTE_BASE"] = "NÃO INFORMADO"
    else:
        df["NOME_CLIENTE_BASE"] = df[col_nome].apply(normalizar_nome)
        df.loc[df["NOME_CLIENTE_BASE"] == "", "NOME_CLIENTE_BASE"] = "NÃO INFORMADO"

    if col_cpf is None:
        df["CPF_CLIENTE_BASE"] = ""
    else:
        df["CPF_CLIENTE_BASE"] = df[col_cpf].apply(limpar_cpf)

    # SITUAÇÃO BASE
    possiveis_cols_situacao = [
        "SITUAÇÃO",
        "SITUAÇÃO ATUAL",
        "STATUS",
        "SITUACAO",
        "SITUACAO ATUAL",
    ]
    col_situacao = next((c for c in possiveis_cols_situacao if c in df.columns), None)

    df["STATUS_BASE"] = ""
    if col_situacao:
        status = df[col_situacao].fillna("").astype(str).str.upper()
        df.loc[status.str.contains("EM ANÁLISE"), "STATUS_BASE"] = "EM ANÁLISE"
        df.loc[status.str.contains("REANÁLISE"), "STATUS_BASE"] = "REANÁLISE"
        df.loc[status.str.contains("APROV"), "STATUS_BASE"] = "APROVADO"
        df.loc[status.str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
        df.loc[status.str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA GERADA"
        df.loc[status.str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA INFORMADA"
        df.loc[status.str.contains("PENDEN"), "STATUS_BASE"] = "PENDÊNCIA"

    # VGV – usando OBSERVAÇÕES quando for valor numérico
    if "OBSERVAÇÕES" in df.columns:
        df["VGV"] = pd.to_numeric(df["OBSERVAÇÕES"], errors="coerce").fillna(0.0)
    else:
        df["VGV"] = 0.0

    # -----------------------------------------------------
    # CHAVE DO CLIENTE — REGRA:
    # 1) Normaliza nome e CPF
    # 2) Se existir algum CPF para aquele nome, todos os registros
    #    desse nome passam a usar o MESMO CPF como chave.
    # 3) Só se não houver nenhum CPF para o nome é que a chave fica sendo o nome.
    # -----------------------------------------------------
    df["NOME_CLIENTE_BASE"] = df["NOME_CLIENTE_BASE"].apply(normalizar_nome)
    df["CPF_CLIENTE_BASE"] = df["CPF_CLIENTE_BASE"].apply(limpar_cpf)

    # chave provisória
    df["CHAVE_CLIENTE"] = df["CPF_CLIENTE_BASE"]
    df.loc[df["CHAVE_CLIENTE"] == "", "CHAVE_CLIENTE"] = df["NOME_CLIENTE_BASE"]

    # mapa nome -> cpf (apenas nomes que têm CPF em pelo menos um registro)
    mapa_nome_cpfs = (
        df[df["CPF_CLIENTE_BASE"] != ""]
        .groupby("NOME_CLIENTE_BASE")["CPF_CLIENTE_BASE"]
        .first()
        .to_dict()
    )

    def corrigir_chave(row):
        nome = row["NOME_CLIENTE_BASE"]
        cpf_real = mapa_nome_cpfs.get(nome, None)
        if cpf_real:
            return cpf_real  # força chave pelo CPF real
        return row["CHAVE_CLIENTE"]

    df["CHAVE_CLIENTE"] = df.apply(corrigir_chave, axis=1)

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
)

termo = st.sidebar.text_input(
    "Digite o nome ou CPF do cliente",
    placeholder="Ex: MARIA / 12345678901",
)

st.sidebar.caption(
    "• Nome: pode digitar só uma parte (ex: 'SILVA')\n"
    "• CPF: digite apenas números (pode colar com ponto/traço que eu limpo)"
)

btn_buscar = st.sidebar.button("Buscar cliente")

# ---------------------------------------------------------
# LÓGICA DE BUSCA
# ---------------------------------------------------------
if not termo and not btn_buscar:
    st.info("Use a barra lateral para buscar um cliente pelo **nome** ou **CPF**.")
    st.stop()

if btn_buscar or termo:
    termo = termo.strip()
    if termo == "":
        st.warning("Digite um nome ou CPF para buscar.")
        st.stop()

    df_busca = df.copy()

    if tipo_busca == "Nome (parcial)":
        termo_up = termo.upper()
        df_busca = df_busca[
            df_busca["NOME_CLIENTE_BASE"].str.contains(termo_up, na=False)
        ]
    else:  # CPF
        termo_cpf = limpar_cpf(termo)
        if termo_cpf == "":
            st.warning("CPF inválido. Digite apenas números.")
            st.stop()
        df_busca = df_busca[df_busca["CPF_CLIENTE_BASE"] == termo_cpf]

    if df_busca.empty:
        st.warning("Nenhum cliente encontrado com esse critério.")
        st.stop()

# ---------------------------------------------------------
# AGRUPAMENTO POR CLIENTE (ÚLTIMA AÇÃO + RESUMO)
# ---------------------------------------------------------
df_busca = df_busca.dropna(subset=["DT_BASE"]).copy()
df_busca = df_busca.sort_values("DT_BASE")

registros = []

for chave, g in df_busca.groupby("CHAVE_CLIENTE", sort=False):
    g = g.sort_values("DT_BASE")

    last = g.iloc[-1]
    status_series = g["STATUS_BASE"].fillna("")

    # Contagens básicas
    analises_em = (status_series == "EM ANÁLISE").sum()
    reanalises = (status_series == "REANÁLISE").sum()
    analises_total = analises_em + reanalises
    aprovacoes = (status_series == "APROVADO").sum()

    # Regra de vendas:
    # - Último status é apenas informativo (last["STATUS_BASE"])
    # - VENDA GERADA anula VENDA INFORMADA na contagem de vendas/VGV
    tem_venda_gerada = (status_series == "VENDA GERADA").any()
    if tem_venda_gerada:
        mask_venda = status_series == "VENDA GERADA"
    else:
        mask_venda = status_series == "VENDA INFORMADA"

    vendas = int(mask_venda.sum())
    vgv = float(g.loc[mask_venda, "VGV"].sum())

    registros.append(
        {
            "CHAVE_CLIENTE": chave,
            "NOME": last["NOME_CLIENTE_BASE"],
            "CPF": last["CPF_CLIENTE_BASE"],
            "ULT_STATUS": last.get("STATUS_BASE", ""),
            "ULT_DATA": last["DT_BASE"],
            "EQUIPE": last.get("EQUIPE", "NÃO INFORMADO"),
            "CORRETOR": last.get("CORRETOR", "NÃO INFORMADO"),
            "ANALISES_EM": int(analises_em),
            "REANALISES": int(reanalises),
            "ANALISES": int(analises_total),
            "APROVACOES": int(aprovacoes),
            "VENDAS": vendas,
            "VGV": vgv,
        }
    )

df_resumo = pd.DataFrame(registros)

if df_resumo.empty:
    st.warning("Não foi possível montar o resumo dos clientes.")
    st.stop()

df_resumo = df_resumo.sort_values("NOME").reset_index(drop=True)

# ---------------------------------------------------------
# VISÃO GERAL (TABELA RESUMO)
# ---------------------------------------------------------
qtde_clientes = df_resumo.shape[0]
st.markdown(f"### 🔍 Resultado da busca – {qtde_clientes} cliente(s) encontrado(s)")

df_visao = df_resumo.copy()
df_visao["ULT_DATA"] = pd.to_datetime(df_visao["ULT_DATA"], errors="coerce").dt.date
df_visao["ULT_DATA"] = df_visao["ULT_DATA"].apply(
    lambda d: d.strftime("%d/%m/%Y")
    if pd.notnull(pd.to_datetime(d, errors="coerce"))
    else ""
)
df_visao["VGV"] = df_visao["VGV"].apply(
    lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
)

df_visao = df_visao[
    ["NOME", "CPF", "ULT_STATUS", "ULT_DATA", "ANALISES", "APROVACOES", "VENDAS", "VGV"]
]

st.markdown("#### 📋 Visão geral")
st.dataframe(df_visao, use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# DETALHE POR CLIENTE
# ---------------------------------------------------------
st.markdown("### 📂 Detalhamento por cliente")

for _, row in df_resumo.iterrows():
    chave = row["CHAVE_CLIENTE"]
    df_cli = df_busca[df_busca["CHAVE_CLIENTE"] == chave].copy()
    df_cli = df_cli.sort_values("DT_BASE")

    analises_em = row["ANALISES_EM"]
    reanalises = row["REANALISES"]
    analises_total = row["ANALISES"]
    aprovacoes = row["APROVACOES"]
    vendas = row["VENDAS"]
    vgv = row["VGV"]

    with st.container():
        st.markdown("---")
        st.markdown(f"##### 👤 {row['NOME']}")

        col_top1, col_top2 = st.columns([2, 3])

        # ------- LADO ESQUERDO: CAMPOS TEXTUAIS -------
        with col_top1:
            cpf_fmt = row["CPF"] if row["CPF"] else "NÃO INFORMADO"
            situacao_fmt = row["ULT_STATUS"] or "NÃO INFORMADO"
            data_ult = (
                pd.to_datetime(row["ULT_DATA"], errors="coerce").strftime("%d/%m/%Y")
                if not pd.isna(row["ULT_DATA"])
                else "NÃO INFORMADO"
            )

            st.write(f"**CPF:** `{cpf_fmt}`")
            st.write(f"**Equipe:** {row['EQUIPE']}")
            st.write(f"**Corretor responsável:** {row['CORRETOR']}")
            st.write(f"**Último status:** {situacao_fmt}")
            st.write(f"**Data da última ação:** {data_ult}")

        # ------- LADO DIREITO: MÉTRICAS -------
        with col_top2:
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Análises (EM)", int(analises_em))
            with m2:
                st.metric("Reanálises", int(reanalises))
            with m3:
                st.metric("Análises (EM + RE)", int(analises_total))

            m4, m5, m6 = st.columns(3)
            with m4:
                st.metric("Aprovações", int(aprovacoes))
            with m5:
                st.metric("Vendas", int(vendas))
            with m6:
                st.metric(
                    "VGV total",
                    f"R$ {vgv:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                )

        # ------- HISTÓRICO DO CLIENTE -------
        st.markdown("###### 📜 Histórico de ações do cliente")

        df_cli_hist = df_cli.copy()
        df_cli_hist["DATA"] = df_cli_hist["DT_BASE"].dt.strftime("%d/%m/%Y")
        df_cli_hist["STATUS"] = df_cli_hist["STATUS_BASE"]

        col_hist = [
            c
            for c in ["DATA", "STATUS", "EQUIPE", "CORRETOR", "OBSERVAÇÕES"]
            if c in df_cli_hist.columns
        ]
        df_cli_hist = df_cli_hist[col_hist]

        st.dataframe(df_cli_hist, use_container_width=True, hide_index=True)
