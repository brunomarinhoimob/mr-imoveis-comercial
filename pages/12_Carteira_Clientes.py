import sys
from pathlib import Path
from datetime import timedelta

import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd

# =========================================================
# PATH
# =========================================================
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from utils.bootstrap import iniciar_app
from utils.data_loader import carregar_dados_planilha

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="Carteira de Clientes",
    page_icon="📂",
    layout="wide"
)
# Auto refresh
st_autorefresh(interval=30 * 1000, key="auto_refresh_carteira")

iniciar_app()

# =========================================================
# CONTEXTO DO USUÁRIO
# =========================================================
perfil = st.session_state.get("perfil")
nome_corretor = st.session_state.get("nome_usuario", "").upper().strip()

# =========================================================
# HEADER
# =========================================================
col_logo, col_title = st.columns([1, 6])

with col_logo:
    try:
        st.image("logo_mr.png", use_container_width=True)
    except:
        st.write("MR IMÓVEIS")

with col_title:
    st.markdown("## 📂 Carteira de Clientes")
    st.caption(
        "Carteira filtrada por período e situação. "
        "Corretores visualizam apenas seus próprios clientes."
    )



# =========================================================
# LOAD DATA (BLINDADO PARA DATA)
# =========================================================
@st.cache_data(ttl=60)
def carregar():
    df = carregar_dados_planilha()
    df.columns = df.columns.str.upper().str.strip()

    # -------------------------
    # DATA — LIMPEZA TOTAL
    # -------------------------
    df["DATA_RAW"] = df["DATA"].astype(str)

    df["DATA_RAW"] = (
        df["DATA_RAW"]
        .str.replace(r"\s+", "", regex=True)
        .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    )

    df["DATA"] = pd.to_datetime(
        df["DATA_RAW"],
        dayfirst=True,
        errors="coerce"
    )

    df = df[df["DATA"].notna()]

    # -------------------------
    # CLIENTE
    # -------------------------
    df["CLIENTE"] = (
        df["CLIENTE"]
        .fillna("")
        .astype(str)
        .str.upper()
        .str.strip()
    )

    # -------------------------
    # CPF
    # -------------------------
    df["CPF"] = (
        df["CPF"]
        .fillna("")
        .astype(str)
        .str.replace(r"\D", "", regex=True)
    )

    # -------------------------
    # CORRETOR / EQUIPE
    # -------------------------
    df["CORRETOR"] = (
        df["CORRETOR"]
        .fillna("")
        .astype(str)
        .str.upper()
        .str.strip()
    )

    df["EQUIPE"] = (
        df["EQUIPE"]
        .fillna("")
        .astype(str)
        .str.upper()
    )

    # -------------------------
    # CONSTRUTORA / EMPREENDIMENTO
    # -------------------------
    df["CONSTRUTORA"] = df.get("CONSTRUTORA", "").fillna("").astype(str).str.upper()
    df["EMPREENDIMENTO"] = df.get("EMPREENDIMENTO", "").fillna("").astype(str).str.upper()

    # -------------------------
    # SITUAÇÃO
    # -------------------------
    col_status = next(
        (c for c in ["SITUAÇÃO", "SITUACAO", "STATUS"] if c in df.columns),
        None
    )

    df["SITUACAO"] = (
        df[col_status].fillna("").astype(str).str.upper()
        if col_status else ""
    )

    # -------------------------
    # VGV
    # -------------------------
    if "VGV" in df.columns:
        df["VGV"] = pd.to_numeric(df["VGV"], errors="coerce").fillna(0)
    else:
        df["VGV"] = 0

    return df


df = carregar()

# =========================================================
# SIDEBAR — FILTROS DE EQUIPE / CORRETOR
# =========================================================
st.sidebar.title("Filtros 🔎")

df_visivel = df.copy()

if perfil == "corretor":
    df_visivel = df_visivel[df_visivel["CORRETOR"] == nome_corretor]
    st.sidebar.info(f"👤 Corretor: {nome_corretor}")
else:
    equipes = sorted([e for e in df_visivel["EQUIPE"].unique() if e])
    equipe_sel = st.sidebar.selectbox(
        "Equipe:",
        ["Todas"] + equipes,
        index=0
    )

    if equipe_sel != "Todas":
        df_visivel = df_visivel[df_visivel["EQUIPE"] == equipe_sel]

    corretores = sorted([c for c in df_visivel["CORRETOR"].unique() if c])
    corretor_sel = st.sidebar.selectbox(
        "Corretor:",
        ["Todos"] + corretores,
        index=0
    )

    if corretor_sel != "Todos":
        df_visivel = df_visivel[df_visivel["CORRETOR"] == corretor_sel]
# ---------------------------------------------------------
# SELETOR DE PERÍODO (TOPO — FORMATO BR)
# ---------------------------------------------------------
st.markdown("---")
col_periodo_esq, col_periodo_dir = st.columns([3, 2])

with col_periodo_dir:
    df_datas = df_visivel[df_visivel["DATA"].notna()]

    dt_min = df_datas["DATA"].min().date()
    dt_max = df_datas["DATA"].max().date()

    inicio_default = max(dt_min, dt_max - timedelta(days=30))

    periodo = st.date_input(
        "📅 Período",
        value=(inicio_default, dt_max),
        min_value=dt_min,
        max_value=dt_max,
        format="DD/MM/YYYY"
    )

dt_ini, dt_fim = periodo

df_visivel = df_visivel[
    (df_visivel["DATA"] >= pd.to_datetime(dt_ini)) &
    (df_visivel["DATA"] <= pd.to_datetime(dt_fim))
]

# =========================================================
# ÚLTIMA SITUAÇÃO POR CLIENTE
# =========================================================
def ultima_linha(grupo: pd.DataFrame) -> pd.Series:
    return grupo.sort_values("DATA").iloc[-1]


df_resumo = (
    df_visivel.groupby(["CLIENTE", "CPF"], as_index=False)
    .apply(ultima_linha)
    .reset_index(drop=True)
)

# =========================================================
# FILTRO POR SITUAÇÃO
# =========================================================
st.markdown("### 🎛️ Filtro por Situação")

situacoes_base = [
    "EM ANÁLISE",
    "APROVAÇÃO",
    "APROVADO BACEN",
    "PENDÊNCIA",
    "REPROVAÇÃO",
    "REANÁLISE",
    "VENDA GERADA",
    "VENDA INFORMADA",
    "DESISTIU",
]

situacoes_sel = st.multiselect(
    "Situações:",
    options=situacoes_base,
    default=situacoes_base
)

df_view = df_resumo.copy()

if situacoes_sel:
    df_view = df_view[df_view["SITUACAO"].isin(situacoes_sel)]

if df_view.empty:
    st.info("Nenhum cliente encontrado com os filtros selecionados.")
    st.stop()

# =========================================================
# DATA FORMATADA
# =========================================================
df_view["DATA_EXIBICAO"] = df_view["DATA"].dt.strftime("%d/%m/%Y")

# =========================================================
# EXIBIÇÃO FINAL
# =========================================================
st.markdown("---")
st.markdown("## 📋 Carteira de Clientes")
st.caption(f"Total de clientes exibidos: {len(df_view)}")

df_view["VGV"] = df_view["VGV"].apply(
    lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
)

st.dataframe(
    df_view[
        [
            "CLIENTE",
            "CPF",
            "EQUIPE",
            "CORRETOR",
            "SITUACAO",
            "DATA_EXIBICAO",
            "CONSTRUTORA",
            "EMPREENDIMENTO",
            "VGV",
        ]
    ].rename(columns={
        "CLIENTE": "Cliente",
        "CPF": "CPF",
        "EQUIPE": "Equipe",
        "CORRETOR": "Corretor",
        "SITUACAO": "Situação atual",
        "DATA_EXIBICAO": "Última movimentação",
        "CONSTRUTORA": "Construtora",
        "EMPREENDIMENTO": "Empreendimento",
    }).sort_values(
        ["Situação atual", "Última movimentação"],
        ascending=[True, False]
    ),
    use_container_width=True,
    hide_index=True
)
