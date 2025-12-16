import streamlit as st
import pandas as pd
from datetime import date, timedelta
if "logado" not in st.session_state or not st.session_state.logado:
    st.warning("🔒 Acesso restrito. Faça login para continuar.")
    st.stop()

from app_dashboard import carregar_dados_planilha

st.set_page_config(page_title="Carteira de Clientes", page_icon="📂", layout="wide")

# ---------------------------------------------------------
# CABEÇALHO
# ---------------------------------------------------------
col_logo, col_titulo = st.columns([1, 4])
with col_logo:
    try:
        st.image("logo_mr.png", use_column_width=True)
    except:
        st.write("MR IMÓVEIS")
with col_titulo:
    st.markdown("## 📂 Carteira de Clientes por Equipe / Corretor")
    st.caption(
        "Filtre clientes por equipe, corretor, período e situação atual.\n"
        "A situação respeita a regra VENDA / DESISTIU."
    )

# ---------------------------------------------------------
# CARREGAR DADOS
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def carregar():
    df = carregar_dados_planilha()
    df.columns = df.columns.str.upper().str.strip()

    # DATA
    if "DIA" in df:
        df["DIA"] = pd.to_datetime(df["DIA"], errors="coerce")
    elif "DATA" in df:
        df["DIA"] = pd.to_datetime(df["DATA"], errors="coerce")

    # CLIENTE
    col_nome = next((c for c in ["NOME_CLIENTE_BASE","NOME","CLIENTE"] if c in df), None)
    df["CLIENTE"] = df[col_nome].fillna("NÃO INFORMADO").str.upper() if col_nome else "NÃO INFORMADO"

    col_cpf = next((c for c in ["CPF_CLIENTE_BASE","CPF"] if c in df), None)
    df["CPF"] = df[col_cpf].fillna("").str.replace(r"\D", "", regex=True) if col_cpf else ""

    # PADRÕES
    df["EQUIPE"] = df.get("EQUIPE","NÃO INFORMADO").fillna("NÃO INFORMADO").str.upper()
    df["CORRETOR"] = df.get("CORRETOR","NÃO INFORMADO").fillna("NÃO INFORMADO").str.upper()
    df["CONSTRUTORA"] = df.get("CONSTRUTORA","").fillna("").str.upper()
    df["EMPREENDIMENTO"] = df.get("EMPREENDIMENTO","").fillna("").str.upper()

    # SITUAÇÃO
    col_sit = next((c for c in ["SITUAÇÃO","SITUACAO","STATUS"] if c in df), None)
    df["SITUACAO_ORIGINAL"] = df[col_sit].fillna("").astype(str) if col_sit else ""
    if "STATUS_BASE" not in df:
        df["STATUS_BASE"] = df["SITUACAO_ORIGINAL"].str.upper()

    # VGV
    df["VGV"] = pd.to_numeric(df.get("VGV", 0), errors="coerce").fillna(0)

    # CHAVE CLIENTE
    df["CHAVE"] = df["CLIENTE"] + "|" + df["CPF"]

    return df

df = carregar()

# ---------------------------------------------------------
# REGRA SITUAÇÃO ATUAL
# ---------------------------------------------------------
def obter_ultima_linha(grupo: pd.DataFrame) -> pd.Series:
    grupo = grupo.sort_values("DIA").copy()

    # reset no DESISTIU
    mask_reset = grupo["SITUACAO_ORIGINAL"].str.contains("DESIST", na=False)
    if mask_reset.any():
        idx_last = grupo[mask_reset].index[-1]
        grupo = grupo.loc[idx_last:]

    vendas = grupo[grupo["STATUS_BASE"].isin(["VENDA GERADA","VENDA INFORMADA"])]
    if not vendas.empty:
        return vendas.iloc[-1]
    return grupo.iloc[-1]

# ---------------------------------------------------------
# FILTROS (SIDEBAR)
# ---------------------------------------------------------
st.sidebar.subheader("Filtros – Carteira")

dt_min = df["DIA"].min()
dt_max = df["DIA"].max()

if pd.isna(dt_min) or pd.isna(dt_max):
    dt_min = date.today()
    dt_max = date.today()
else:
    dt_min = dt_min.date()
    dt_max = dt_max.date()

# 👉 LÓGICA BR: padrão últimos 30 dias (ou menos, se não tiver tudo isso)
inicio_default = max(dt_min, dt_max - timedelta(days=30))
fim_default = dt_max

periodo = st.sidebar.date_input(
    "Período (dd/mm/aaaa):",
    value=(inicio_default, fim_default),
    min_value=dt_min,
    max_value=dt_max,
)

if isinstance(periodo, tuple):
    dt_ini, dt_fim = periodo
else:
    dt_ini = periodo
    dt_fim = periodo

df = df[(df["DIA"] >= pd.to_datetime(dt_ini)) & (df["DIA"] <= pd.to_datetime(dt_fim))]
# ---------------------------------------------------------
# BLOQUEIO REAL DE DADOS PARA PERFIL CORRETOR
# ---------------------------------------------------------
if perfil == "corretor":
    df = df[df["CORRETOR"] == nome_corretor_logado]

perfil = st.session_state.get("perfil")
nome_corretor_logado = st.session_state.get("nome_usuario", "").upper()
nome_corretor_logado = nome_corretor_logado.strip()

if perfil == "corretor":
    equipe = "Todas"
    corretor = nome_corretor_logado
    st.sidebar.info(f"👤 Corretor logado: {nome_corretor_logado}")
else:
    equipe = st.sidebar.selectbox("Equipe:", ["Todas"] + sorted(df["EQUIPE"].unique()))
    corretor = st.sidebar.selectbox("Corretor:", ["Todos"] + sorted(df["CORRETOR"].unique()))
if corretor != "Todos":
    df = df[df["CORRETOR"] == corretor]

if equipe != "Todas":
    df = df[df["EQUIPE"] == equipe]

if df.empty:
    st.info("Nenhum cliente encontrado com esses filtros.")
    st.stop()

# ---------------------------------------------------------
# MONTAR CARTEIRA
# ---------------------------------------------------------
resumo = []
for (ch, corr), grupo in df.groupby(["CHAVE", "CORRETOR"]):
    linha = obter_ultima_linha(grupo)

    historico = grupo["STATUS_BASE"]
    resumo.append({
        "Cliente": linha["CLIENTE"],
        "CPF": linha["CPF"],
        "Equipe": linha["EQUIPE"],
        "Corretor": linha["CORRETOR"],
        "Situação atual": linha["SITUACAO_ORIGINAL"],
        "Última movimentação": linha["DIA"],
        "Construtora": linha["CONSTRUTORA"],
        "Empreendimento": linha["EMPREENDIMENTO"],
        "Análises": historico.isin(["EM ANÁLISE","REANÁLISE"]).sum(),
        "Aprovações": (historico == "APROVADO").sum(),
        "Vendas": historico.isin(["VENDA GERADA","VENDA INFORMADA"]).sum(),
        "VGV": grupo["VGV"].sum()
    })

df_resumo = pd.DataFrame(resumo)

# ---------------------------------------------------------
# FILTRO POR SITUAÇÃO (MULTISELECT)
# ---------------------------------------------------------
st.markdown("### 🎛️ Filtro por Situação do Cliente")

situacoes = sorted(df_resumo["Situação atual"].dropna().unique().tolist())

situacoes_select = st.multiselect(
    "Selecione as situações:",
    options=situacoes,
    default=situacoes,
)

if situacoes_select:
    df_resumo = df_resumo[df_resumo["Situação atual"].isin(situacoes_select)]

# FORMATAÇÃO
df_resumo["Última movimentação"] = pd.to_datetime(df_resumo["Última movimentação"]).dt.strftime("%d/%m/%Y")
df_resumo["VGV"] = df_resumo["VGV"].apply(
    lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X",".")
)

st.markdown("---")
st.markdown("### 🧾 Carteira de clientes do período")
st.caption(f"Total de clientes exibidos: {len(df_resumo)}")

st.dataframe(
    df_resumo.sort_values(["Corretor","Situação atual","Cliente"]),
    use_container_width=True,
    hide_index=True
)
