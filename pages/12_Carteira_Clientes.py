import streamlit as st
import pandas as pd
from datetime import date, timedelta

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA (PRIMEIRA COISA DO ARQUIVO)
# ---------------------------------------------------------
st.set_page_config(
    page_title="Carteira de Clientes",
    page_icon="📂",
    layout="wide"
)

from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=30 * 1000, key="auto_refresh_global")

# ---------------------------------------------------------
# IMPORTS DE NEGÓCIO
# ---------------------------------------------------------
from utils.bootstrap import iniciar_app
from app_dashboard import carregar_dados_planilha

# ---------------------------------------------------------
# BOOTSTRAP GLOBAL (LOGIN + NOTIFICAÇÕES) — UMA ÚNICA VEZ
# ---------------------------------------------------------
iniciar_app()

# ---------------------------------------------------------
# CONTEXTO DO USUÁRIO LOGADO
# ---------------------------------------------------------

perfil = st.session_state.get("perfil")
nome_corretor_logado = (
    st.session_state.get("nome_usuario", "")
    .upper()
    .strip()
)

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
    st.markdown("## 📂 Carteira de Clientes")
    st.caption(
        "Carteira filtrada por período e perfil de acesso. "
        "Corretores visualizam apenas seus próprios clientes."
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
    else:
        df["DIA"] = pd.NaT

    # CLIENTE
    col_nome = next(
        (c for c in ["NOME_CLIENTE_BASE", "NOME", "CLIENTE"] if c in df),
        None
    )
    df["CLIENTE"] = (
        df[col_nome].fillna("NÃO INFORMADO").str.upper()
        if col_nome else "NÃO INFORMADO"
    )

    col_cpf = next(
        (c for c in ["CPF_CLIENTE_BASE", "CPF"] if c in df),
        None
    )
    df["CPF"] = (
        df[col_cpf].fillna("").str.replace(r"\D", "", regex=True)
        if col_cpf else ""
    )

    # PADRÕES
    df["EQUIPE"] = df.get("EQUIPE", "NÃO INFORMADO").fillna("NÃO INFORMADO").str.upper()
    df["CORRETOR"] = df.get("CORRETOR", "NÃO INFORMADO").fillna("NÃO INFORMADO").str.upper()
    df["CONSTRUTORA"] = df.get("CONSTRUTORA", "").fillna("").str.upper()
    df["EMPREENDIMENTO"] = df.get("EMPREENDIMENTO", "").fillna("").str.upper()

    # SITUAÇÃO
    col_sit = next(
        (c for c in ["SITUAÇÃO", "SITUACAO", "STATUS"] if c in df),
        None
    )
    df["SITUACAO_ORIGINAL"] = df[col_sit].fillna("").astype(str) if col_sit else ""
    df["STATUS_BASE"] = df["SITUACAO_ORIGINAL"].str.upper()

    # VGV
    df["VGV"] = pd.to_numeric(df.get("VGV", 0), errors="coerce").fillna(0)

    # CHAVE CLIENTE
    df["CHAVE"] = df["CLIENTE"] + "|" + df["CPF"]

    return df


df = carregar()

# ---------------------------------------------------------
# FILTRO DE PERÍODO
# ---------------------------------------------------------
dt_min = df["DIA"].min()
dt_max = df["DIA"].max()

if pd.isna(dt_min) or pd.isna(dt_max):
    dt_min = date.today()
    dt_max = date.today()
else:
    dt_min = dt_min.date()
    dt_max = dt_max.date()

inicio_default = max(dt_min, dt_max - timedelta(days=30))
fim_default = dt_max

st.sidebar.subheader("Filtros – Carteira")

periodo = st.sidebar.date_input(
    "Período:",
    value=(inicio_default, fim_default),
    min_value=dt_min,
    max_value=dt_max
)

if isinstance(periodo, tuple):
    dt_ini, dt_fim = periodo
else:
    dt_ini = periodo
    dt_fim = periodo

df = df[
    (df["DIA"] >= pd.to_datetime(dt_ini)) &
    (df["DIA"] <= pd.to_datetime(dt_fim))
]

# ---------------------------------------------------------
# BLOQUEIO REAL DE DADOS PARA PERFIL CORRETOR
# ---------------------------------------------------------
if perfil == "corretor":
    df = df[df["CORRETOR"] == nome_corretor_logado]

# ---------------------------------------------------------
# FILTROS SIDEBAR (APENAS ADMIN / GESTOR)
# ---------------------------------------------------------
if perfil == "corretor":
    equipe = "Todas"
    corretor = nome_corretor_logado
    st.sidebar.info(f"👤 Corretor logado: {nome_corretor_logado}")
else:
    equipe = st.sidebar.selectbox(
        "Equipe:",
        ["Todas"] + sorted(df["EQUIPE"].unique())
    )
    corretor = st.sidebar.selectbox(
        "Corretor:",
        ["Todos"] + sorted(df["CORRETOR"].unique())
    )

    if corretor != "Todos":
        df = df[df["CORRETOR"] == corretor]

    if equipe != "Todas":
        df = df[df["EQUIPE"] == equipe]

if df.empty:
    st.info("Nenhum cliente encontrado com os filtros selecionados.")
    st.stop()

# ---------------------------------------------------------
# REGRA DE SITUAÇÃO ATUAL
# ---------------------------------------------------------
def obter_ultima_linha(grupo: pd.DataFrame) -> pd.Series:
    grupo = grupo.sort_values("DIA").copy()

    mask_reset = grupo["SITUACAO_ORIGINAL"].str.contains("DESIST", na=False)
    if mask_reset.any():
        idx_last = grupo[mask_reset].index[-1]
        grupo = grupo.loc[idx_last:]

    vendas = grupo[grupo["STATUS_BASE"].isin(["VENDA GERADA", "VENDA INFORMADA"])]
    if not vendas.empty:
        return vendas.iloc[-1]

    return grupo.iloc[-1]

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
        "Última movimentação": linha["DIA"].strftime("%d/%m/%Y") if pd.notna(linha["DIA"]) else "",
        "Construtora": linha["CONSTRUTORA"],
        "Empreendimento": linha["EMPREENDIMENTO"],
        "Análises": historico.isin(["EM ANÁLISE", "REANÁLISE"]).sum(),
        "Aprovações": (historico == "APROVADO").sum(),
        "Vendas": historico.isin(["VENDA GERADA", "VENDA INFORMADA"]).sum(),
        "VGV": grupo["VGV"].sum()
    })

df_resumo = pd.DataFrame(resumo)

# ---------------------------------------------------------
# FILTRO POR SITUAÇÃO
# ---------------------------------------------------------
st.markdown("### 🎛️ Filtro por Situação")

situacoes = sorted(df_resumo["Situação atual"].dropna().unique().tolist())

selecionadas = st.multiselect(
    "Situações:",
    options=situacoes,
    default=situacoes
)

if selecionadas:
    df_resumo = df_resumo[df_resumo["Situação atual"].isin(selecionadas)]

# ---------------------------------------------------------
# FORMATAÇÃO FINAL
# ---------------------------------------------------------
df_resumo["VGV"] = df_resumo["VGV"].apply(
    lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
)

st.markdown("---")
st.markdown("### 🧾 Carteira de Clientes")
st.caption(f"Total de clientes exibidos: {len(df_resumo)}")

st.dataframe(
    df_resumo.sort_values(["Corretor", "Situação atual", "Cliente"]),
    use_container_width=True,
    hide_index=True
)
