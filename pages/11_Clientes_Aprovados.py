import streamlit as st
import pandas as pd
from datetime import date, timedelta

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Clientes Aprovados – MR Imóveis",
    page_icon="✅",
    layout="wide",
)

# ---------------------------------------------------------
# LOGO MR IMÓVEIS
# ---------------------------------------------------------
LOGO_PATH = "logo_mr.png"

col_logo, col_tit = st.columns([1, 4])
with col_logo:
    try:
        st.image(LOGO_PATH, use_column_width=True)
    except Exception:
        st.write("MR Imóveis")

with col_tit:
    st.markdown("## Clientes Aprovados")
    st.caption(
        "Aqui aparecem apenas clientes cuja **situação atual** está como "
        "**APROVAÇÃO** (ou seja, a última ação registrada na base contém exatamente esse texto)."
    )

# ---------------------------------------------------------
# FUNÇÃO AUXILIAR PARA LIMPAR DATA
# ---------------------------------------------------------
def limpar_para_data(serie):
    dt = pd.to_datetime(serie, dayfirst=True, errors="coerce")
    return dt.dt.date

# ---------------------------------------------------------
# CONFIG: LINK DA PLANILHA (MESMO DA PÁGINA CLIENTES EM ANÁLISE)
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
            df[col] = df[col].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
        else:
            df[col] = "NÃO INFORMADO"

    # CONSTRUTORA / EMPREENDIMENTO
    possiveis_construtora = ["CONSTRUTORA", "INCORPORADORA"]
    possiveis_empreend = ["EMPREENDIMENTO", "PRODUTO", "IMÓVEL", "IMOVEL"]

    col_construtora = None
    for c in possiveis_construtora:
        if c in df.columns:
            col_construtora = c
            break

    col_empreend = None
    for c in possiveis_empreend:
        if c in df.columns:
            col_empreend = c
            break

    df["CONSTRUTORA_BASE"] = (
        df[col_construtora].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
        if col_construtora else "NÃO INFORMADO"
    )
    df["EMPREENDIMENTO_BASE"] = (
        df[col_empreend].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
        if col_empreend else "NÃO INFORMADO"
    )

    # STATUS BASE — ALTERAÇÃO PEDIDA
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
        status = df[col_situacao].fillna("").astype(str).str.upper().str.strip()

        df.loc[status.str.contains("EM ANÁLISE"), "STATUS_BASE"] = "EM ANÁLISE"
        df.loc[status.str.contains("REANÁLISE"), "STATUS_BASE"] = "REANÁLISE"

        # *** ALTERAÇÃO AQUI ***
        # Agora só conta "APROVAÇÃO" exatamente
        df.loc[status.str.contains(r"\bAPROVAÇÃO\b"), "STATUS_BASE"] = "APROVADO"

        df.loc[status.str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
        df.loc[status.str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA GERADA"
        df.loc[status.str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA INFORMADA"

        df["SITUACAO_ORIGINAL"] = status
    else:
        df["SITUACAO_ORIGINAL"] = "NÃO INFORMADO"

    # OBS / VGV
    if "OBSERVAÇÕES" in df.columns:
        df["OBSERVACOES_RAW"] = df["OBSERVAÇÕES"].fillna("").astype(str).str.strip()
        df["VGV"] = pd.to_numeric(df["OBSERVAÇÕES"], errors="coerce").fillna(0.0)
    else:
        df["OBSERVACOES_RAW"] = ""
        df["VGV"] = 0.0

    # NOME / CPF
    possiveis_nome = ["NOME", "CLIENTE", "NOME CLIENTE", "NOME DO CLIENTE"]
    possiveis_cpf = ["CPF", "CPF CLIENTE", "CPF DO CLIENTE"]

    col_nome = next((c for c in possiveis_nome if c in df.columns), None)
    col_cpf = next((c for c in possiveis_cpf if c in df.columns), None)

    df["NOME_CLIENTE_BASE"] = (
        df[col_nome].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
        if col_nome else "NÃO INFORMADO"
    )

    df["CPF_CLIENTE_BASE"] = (
        df[col_cpf].fillna("").astype(str).str.replace(r"\D", "", regex=True)
        if col_cpf else ""
    )

    df["CHAVE_CLIENTE"] = (
        df["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO")
        + " | "
        + df["CPF_CLIENTE_BASE"].fillna("")
    )

    return df

df = carregar_dados()

if df.empty:
    st.error("Não foi possível carregar dados da planilha.")
    st.stop()

# ---------------------------------------------------------
# DEFINIÇÕES BÁSICAS
# ---------------------------------------------------------
if "NOME_CLIENTE_BASE" in df.columns:
    col_cliente = "NOME_CLIENTE_BASE"
else:
    st.error("Não encontrei coluna de cliente na base.")
    st.stop()

df["DIA"] = pd.to_datetime(df["DIA"], errors="coerce")
df_valid = df.dropna(subset=["DIA"]).copy()
df_valid = df_valid.sort_values(by=[col_cliente, "DIA"])

# Última linha por cliente
df_status_atual = df_valid.drop_duplicates(subset=[col_cliente], keep="last").copy()

# *** ALTERAÇÃO AQUI ***
df_aprovados_atual = df_status_atual[df_status_atual["STATUS_BASE"] == "APROVADO"].copy()

if df_aprovados_atual.empty:
    st.info("No momento não há clientes com APROVAÇÃO registrada.")
    st.stop()

# ---------------------------------------------------------
# BUSCA
# ---------------------------------------------------------
st.sidebar.title("Busca de clientes aprovados 🔎")

tipo_busca = st.sidebar.radio("Buscar por:", ("Nome (parcial)", "CPF"))
termo_busca = st.sidebar.text_input("Digite o nome ou CPF", "")

# ---------------------------------------------------------
# PERÍODO
# ---------------------------------------------------------
st.markdown("### 📅 Período das aprovações")

periodo = st.radio("Selecione:", [7, 15, 30, 60, 90], index=2, horizontal=True)
data_ref = df_valid["DIA"].max()
limite_tempo = data_ref - timedelta(days=periodo)

df_aprovados_periodo = df_aprovados_atual[df_aprovados_atual["DIA"] >= limite_tempo].copy()

if df_aprovados_periodo.empty:
    st.info(f"Não há aprovação nos últimos {periodo} dias.")
    st.stop()

# ---------------------------------------------------------
# FILTRO EQUIPE
# ---------------------------------------------------------
df_filtrado = df_aprovados_periodo.copy()

st.markdown("Filtrar por equipe:")
if "EQUIPE" in df_filtrado.columns:
    equipes = sorted(df_filtrado["EQUIPE"].dropna().unique().tolist())
    equipe_sel = st.selectbox("", ["Todas"] + equipes, index=0)

    if equipe_sel != "Todas":
        df_filtrado = df_filtrado[df_filtrado["EQUIPE"] == equipe_sel]

# ---------------------------------------------------------
# FILTRO CORRETOR
# ---------------------------------------------------------
st.markdown("Filtrar por corretor:")
if "CORRETOR" in df_filtrado.columns:
    corretores = sorted(df_filtrado["CORRETOR"].dropna().unique().tolist())
    corretor_sel = st.selectbox("", ["Todos"] + corretores, index=0)

    if corretor_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado["CORRETOR"] == corretor_sel]

if df_filtrado.empty:
    st.info("Nenhum cliente aprovado dentro desse filtro.")
    st.stop()

# ---------------------------------------------------------
# CARDS GERAIS
# ---------------------------------------------------------
total_aprovados = len(df_filtrado)
equipes_com_aprovados = df_filtrado["EQUIPE"].nunique()
vgv_total = df_filtrado["VGV"].sum()
ticket_medio = vgv_total / max(total_aprovados, 1)

def format_currency(valor):
    return (
        f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

c1, c2, c3 = st.columns(3)
c1.metric("Clientes aprovados", total_aprovados)
c2.metric("Período (dias)", int(periodo))
c3.metric("Equipes com aprovação", int(equipes_com_aprovados))

k1, k2, k3 = st.columns(3)
k1.metric("VGV total", format_currency(vgv_total))
k2.metric("Ticket médio", format_currency(ticket_medio))
k3.metric("Média por equipe", f"{total_aprovados / max(equipes_com_aprovados,1):.1f}")

# ---------------------------------------------------------
# TABELA CLEAN
# ---------------------------------------------------------
st.markdown("---")
st.markdown("### 📋 Lista de clientes com APROVAÇÃO")

colunas_preferidas = [
    "NOME_CLIENTE_BASE",
    "CPF_CLIENTE_BASE",
    "EQUIPE",
    "CORRETOR",
    "EMPREENDIMENTO_BASE",
    "STATUS_BASE",
    "DIA",
]

colunas_existentes = [c for c in colunas_preferidas if c in df_filtrado.columns]
df_tabela = df_filtrado[colunas_existentes].copy()

df_tabela["DIA"] = df_tabela["DIA"].dt.strftime("%d/%m/%Y")

df_tabela = df_tabela.rename(
    columns={
        "NOME_CLIENTE_BASE": "Cliente",
        "CPF_CLIENTE_BASE": "CPF",
        "EQUIPE": "Equipe",
        "CORRETOR": "Corretor",
        "EMPREENDIMENTO_BASE": "Empreendimento",
        "STATUS_BASE": "Status",
        "DIA": "Última atualização",
    }
)

df_tabela = df_tabela.sort_values("Última atualização", ascending=False)

st.dataframe(df_tabela, use_container_width=True, hide_index=True)
