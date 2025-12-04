import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import timedelta, datetime

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# (Em app multipage, isso aqui só é considerado se não tiver no app principal)
# ---------------------------------------------------------
st.set_page_config(
    page_title="Ranking por Corretor – MR Imóveis",
    page_icon="🏆",
    layout="wide",
)

st.title("🏆 Ranking por Corretor – MR Imóveis")

# ---------------------------------------------------------
# CONFIG: LINK DA PLANILHA
# ---------------------------------------------------------
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID_ANALISES = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ANALISES}"

# ---------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------
def limpar_para_data(serie: pd.Series) -> pd.Series:
    dt = pd.to_datetime(serie, dayfirst=True, errors="coerce")
    return dt.dt.date


def mes_ano_ptbr_para_date(valor: str):
    """
    Converte textos tipo 'novembro 2025' em date(2025, 11, 1).
    Se não conseguir, retorna NaT.
    """
    if pd.isna(valor):
        return pd.NaT
    s = str(valor).strip().lower()
    if not s:
        return pd.NaT

    meses = {
        "janeiro": 1,
        "fevereiro": 2,
        "março": 3,
        "marco": 3,
        "abril": 4,
        "maio": 5,
        "junho": 6,
        "julho": 7,
        "agosto": 8,
        "setembro": 9,
        "outubro": 10,
        "novembro": 11,
        "dezembro": 12,
    }

    partes = s.split()
    try:
        mes_txt = partes[0]
        ano = int(partes[-1])
        mes_num = meses.get(mes_txt)
        if mes_num is None:
            return pd.NaT
        return datetime(ano, mes_num, 1).date()
    except Exception:
        return pd.NaT

# ---------------------------------------------------------
# CARREGAR DADOS
# ---------------------------------------------------------
def carregar_dados() -> pd.DataFrame:
    df = pd.read_csv(CSV_URL)

    # Padroniza nomes de colunas
    df.columns = [c.strip().upper() for c in df.columns]

    # DATA (DIA)
    if "DATA" in df.columns:
        df["DIA"] = limpar_para_data(df["DATA"])
    elif "DIA" in df.columns:
        df["DIA"] = limpar_para_data(df["DIA"])
    else:
        df["DIA"] = pd.NaT

    # DATA BASE (MÊS COMERCIAL) - TEXTO IGUAL À PLANILHA + REFERÊNCIA DE DATA
    possiveis_cols_base = [
        "DATA BASE",
        "DATA_BASE",
        "DT BASE",
        "DATA REF",
        "DATA REFERÊNCIA",
        "DATA REFERENCIA",
    ]
    col_data_base = next((c for c in possiveis_cols_base if c in df.columns), None)

    if col_data_base:
        base_raw = df[col_data_base].astype(str).str.strip()
        # Label igual à planilha, só organizando capitalização
        df["DATA_BASE_LABEL"] = base_raw.str.lower().str.title()
        # Converte "novembro 2025" -> 2025-11-01 para ordenar
        df["DATA_BASE"] = base_raw.apply(mes_ano_ptbr_para_date)

        # Se não conseguir converter nenhum, cai para DIA
        if df["DATA_BASE"].dropna().empty:
            df["DATA_BASE"] = df["DIA"]
            df["DATA_BASE_LABEL"] = df["DIA"].apply(
                lambda d: d.strftime("%m/%Y") if pd.notnull(d) else ""
            )
    else:
        # Sem coluna de data base: usa DIA como base
        df["DATA_BASE"] = df["DIA"]
        df["DATA_BASE_LABEL"] = df["DIA"].apply(
            lambda d: d.strftime("%m/%Y") if pd.notnull(d) else ""
        )

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

    # STATUS_BASE
    possiveis_cols_situacao = [
        "SITUAÇÃO",
        "SITUAÇÃO ATUAL",
        "STATUS",
        "SITUACAO",
        "SITUACAO ATUAL",
    ]
    col_situacao = next((c for c in possiveis_cols_situacao if c in df.columns), None)

    df["STATUS_BASE"] = ""
    if col_situacao is not None:
        s = df[col_situacao].fillna("").astype(str).str.upper()
        df.loc[s.str.contains("EM ANÁLISE"), "STATUS_BASE"] = "EM ANÁLISE"
        df.loc[s.str.contains("REANÁLISE"), "STATUS_BASE"] = "REANÁLISE"
        df.loc[s.str.contains("APROV"), "STATUS_BASE"] = "APROVADO"
        df.loc[s.str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
        df.loc[s.str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA GERADA"
        df.loc[s.str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA INFORMADA"
        # 👇 NOVO – mapeia qualquer coisa com DESIST (DESISTIU, DESISTÊNCIA etc.)
        df.loc[s.str.contains("DESIST"), "STATUS_BASE"] = "DESISTIU"

    # VGV (OBSERVAÇÕES)
    if "OBSERVAÇÕES" in df.columns:
        df["VGV"] = pd.to_numeric(df["OBSERVAÇÕES"], errors="coerce").fillna(0)
    else:
        df["VGV"] = 0.0

    # Nome / CPF base para chave de cliente
    possiveis_nome = ["NOME", "CLIENTE", "NOME CLIENTE", "NOME DO CLIENTE"]
    possiveis_cpf = ["CPF", "CPF CLIENTE", "CPF DO CLIENTE"]

    col_nome = next((c for c in possiveis_nome if c in df.columns), None)
    col_cpf = next((c for c in possiveis_cpf if c in df.columns), None)

    if col_nome is None:
        df["NOME_CLIENTE_BASE"] = "NÃO INFORMADO"
    else:
        df["NOME_CLIENTE_BASE"] = (
            df[col_nome].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
        )

    if col_cpf is None:
        df["CPF_CLIENTE_BASE"] = ""
    else:
        df["CPF_CLIENTE_BASE"] = (
            df[col_cpf]
            .fillna("")
            .astype(str)
            .str.replace(r"\D", "", regex=True)
        )

    # 👇 NOVO – CHAVE_CLIENTE global (nome + CPF)
    df["CHAVE_CLIENTE"] = (
        df["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO")
        + " | "
        + df["CPF_CLIENTE_BASE"].fillna("")
    )

    return df

# ---------------------------------------------------------
# CARREGAR BASE
# ---------------------------------------------------------
df = carregar_dados()

if df.empty:
    st.error("Erro ao carregar planilha.")
    st.stop()

# Garante que temos pelo menos algumas datas válidas
dias_validos = df["DIA"].dropna()
bases_validas = df["DATA_BASE"].dropna()

if dias_validos.empty and bases_validas.empty:
    st.error("Não foi possível identificar datas válidas na planilha.")
    st.stop()

# ---------------------------------------------------------
# NOVO – STATUS FINAL DO CLIENTE (HISTÓRICO COMPLETO)
# ---------------------------------------------------------
df_ordenado_global = df.sort_values("DIA")
status_final_por_cliente = (
    df_ordenado_global.groupby("CHAVE_CLIENTE")["STATUS_BASE"].last().fillna("")
)
status_final_por_cliente.name = "STATUS_FINAL_CLIENTE"

# ---------------------------------------------------------
# SIDEBAR – FILTROS (PERÍODO + EQUIPE + TIPO DE VENDA)
# ---------------------------------------------------------
st.sidebar.title("Filtros 🔎")

# Modo de filtro: por dia ou por mês comercial (data base)
modo_periodo = st.sidebar.radio(
    "Modo de filtro do período",
    ["Por DIA (data do registro)", "Por DATA BASE (mês comercial)"],
    index=0,
)

tipo_periodo = "DIA"
data_ini = None
data_fim = None
bases_selecionadas = []

if modo_periodo.startswith("Por DIA"):
    tipo_periodo = "DIA"
    data_min = dias_validos.min()
    data_max = dias_validos.max()
    data_ini_default = max(data_min, data_max - timedelta(days=30))

    periodo = st.sidebar.date_input(
        "Período (DIA)",
        value=(data_ini_default, data_max),
        min_value=data_min,
        max_value=data_max,
    )
    data_ini, data_fim = periodo
else:
    tipo_periodo = "DATA_BASE"

    # monta lista de meses base ordenados
    bases_df = (
        df[["DATA_BASE", "DATA_BASE_LABEL"]]
        .dropna(subset=["DATA_BASE"])
        .drop_duplicates()
        .sort_values("DATA_BASE")
    )

    opcoes = bases_df["DATA_BASE_LABEL"].tolist()

    if not opcoes:
        st.error("Sem datas base válidas na planilha para filtrar.")
        st.stop()

    default_labels = opcoes[-2:] if len(opcoes) >= 2 else opcoes

    bases_selecionadas = st.sidebar.multiselect(
        "Período por DATA BASE (mês comercial)",
        options=opcoes,
        default=default_labels,
    )

    if not bases_selecionadas:
        bases_selecionadas = opcoes

lista_equipes = sorted(df["EQUIPE"].unique())
equipe_sel = st.sidebar.selectbox("Equipe (opcional)", ["Todas"] + lista_equipes)

# NOVO FILTRO – tipo de venda a considerar
opcao_venda = st.sidebar.radio(
    "Tipo de venda para o ranking",
    ("VENDA GERADA + INFORMADA", "Só VENDA GERADA"),
    index=0,
)

if opcao_venda == "Só VENDA GERADA":
    status_venda_considerado = ["VENDA GERADA"]
    desc_venda = "apenas VENDA GERADA"
else:
    status_venda_considerado = ["VENDA GERADA", "VENDA INFORMADA"]
    desc_venda = "VENDA GERADA + VENDA INFORMADA"

# ---------------------------------------------------------
# FILTRAGEM PRINCIPAL (PERÍODO + EQUIPE)
# ---------------------------------------------------------
if tipo_periodo == "DIA":
    df_ref = df[
        (df["DIA"] >= data_ini) &
        (df["DIA"] <= data_fim)
    ].copy()
else:
    df_ref = df[df["DATA_BASE_LABEL"].isin(bases_selecionadas)].copy()
    # calcula o intervalo real de dias desse(s) mês(es) para exibir no texto, se quiser
    dias_sel = df_ref["DIA"].dropna()
    if not dias_sel.empty:
        data_ini = dias_sel.min()
        data_fim = dias_sel.max()
    else:
        data_ini = dias_validos.min()
        data_fim = dias_validos.max()

if equipe_sel != "Todas":
    df_ref = df_ref[df_ref["EQUIPE"] == equipe_sel]

registros_ref = len(df_ref)

# Texto do período para caption
if tipo_periodo == "DIA":
    periodo_str = f"{data_ini.strftime('%d/%m/%Y')} até {data_fim.strftime('%d/%m/%Y')}"
else:
    if len(bases_selecionadas) == 1:
        periodo_str = bases_selecionadas[0]
    else:
        periodo_str = f"{bases_selecionadas[0]} até {bases_selecionadas[-1]}"

if df_ref.empty:
    st.caption(
        f"Período: {periodo_str}"
        + ("" if equipe_sel == "Todas" else f" • Equipe: {equipe_sel}")
        + f" • Registros na base: 0"
        + f" • Vendas consideradas no ranking: {desc_venda}"
    )
    st.warning("Sem registros para os filtros selecionados.")
    st.stop()

st.caption(
    f"Período: {periodo_str}"
    + ("" if equipe_sel == "Todas" else f" • Equipe: {equipe_sel}")
    + f" • Registros na base: {registros_ref}"
    + f" • Vendas consideradas no ranking: {desc_venda}"
)

# ---------------------------------------------------------
# CÁLCULOS DE RANKING
# ---------------------------------------------------------

# Análises = EM ANÁLISE + REANÁLISE
mask_analises = df_ref["STATUS_BASE"].isin(["EM ANÁLISE", "REANÁLISE"])
df_analises = df_ref[mask_analises]

analises_por_corretor = (
    df_analises.groupby("CORRETOR").size().rename("ANALISES")
)

# Aprovações
df_aprov = df_ref[df_ref["STATUS_BASE"] == "APROVADO"]
aprov_por_corretor = df_aprov.groupby("CORRETOR").size().rename("APROVACOES")

# ---------------------------------------------------------
# Vendas (1 por cliente) e VGV – com REGRA DO DESISTIU
# ---------------------------------------------------------
df_vendas = df_ref[df_ref["STATUS_BASE"].isin(status_venda_considerado)].copy()

if not df_vendas.empty:

    # Garante CHAVE_CLIENTE
    if "CHAVE_CLIENTE" not in df_vendas.columns:
        df_vendas["CHAVE_CLIENTE"] = (
            df_vendas["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO")
            + " | "
            + df_vendas["CPF_CLIENTE_BASE"].fillna("")
        )

    # Junta o STATUS_FINAL_CLIENTE vindo do histórico completo
    df_vendas = df_vendas.merge(
        status_final_por_cliente,
        on="CHAVE_CLIENTE",
        how="left",
    )

    # Remove clientes cujo último status global é DESISTIU
    df_vendas = df_vendas[df_vendas["STATUS_FINAL_CLIENTE"] != "DESISTIU"]

    if not df_vendas.empty:
        df_vendas = df_vendas.sort_values("DIA")
        # 1 registro por cliente (o último do período)
        df_vendas_ult = df_vendas.groupby("CHAVE_CLIENTE").tail(1)
    else:
        df_vendas_ult = pd.DataFrame()
else:
    df_vendas_ult = pd.DataFrame()

vendas_por_corretor = (
    df_vendas_ult.groupby("CORRETOR").size().rename("VENDAS")
    if not df_vendas_ult.empty
    else pd.Series(dtype=int, name="VENDAS")
)

vgv_por_corretor = (
    df_vendas_ult.groupby("CORRETOR")["VGV"].sum().rename("VGV")
    if not df_vendas_ult.empty
    else pd.Series(dtype=float, name="VGV")
)

# Junta tudo
ranking = (
    pd.concat(
        [analises_por_corretor, aprov_por_corretor, vendas_por_corretor, vgv_por_corretor],
        axis=1,
    )
    .fillna(0)
    .reset_index()
)

if ranking.empty:
    st.warning("Não há dados suficientes para montar o ranking.")
    st.stop()

# Garante tipos
ranking["ANALISES"] = ranking["ANALISES"].astype(int)
ranking["APROVACOES"] = ranking["APROVACOES"].astype(int)
ranking["VENDAS"] = ranking["VENDAS"].astype(int)
ranking["VGV"] = ranking["VGV"].astype(float)

# Taxas
ranking["TAXA_APROV_ANALISES"] = np.where(
    ranking["ANALISES"] > 0,
    ranking["APROVACOES"] / ranking["ANALISES"] * 100,
    0.0,
)
ranking["TAXA_VENDAS_ANALISES"] = np.where(
    ranking["ANALISES"] > 0,
    ranking["VENDAS"] / ranking["ANALISES"] * 100,
    0.0,
)

# Ordenação do ranking: VGV, VENDAS, APROVACOES, ANALISES
ranking = ranking.sort_values(
    by=["VGV", "VENDAS", "APROVACOES", "ANALISES"],
    ascending=[False, False, False, False],
).reset_index(drop=True)

# Posição com medalhas
posicoes = []
for i in range(len(ranking)):
    pos = i + 1
    if pos == 1:
        posicoes.append("🥇 1º")
    elif pos == 2:
        posicoes.append("🥈 2º")
    elif pos == 3:
        posicoes.append("🥉 3º")
    else:
        posicoes.append(f"{pos}º")

ranking["POSICAO"] = posicoes

# ---------------------------------------------------------
# FORMATAÇÃO
# ---------------------------------------------------------
def formata_moeda(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

ranking["VGV_FMT"] = ranking["VGV"].apply(formata_moeda)
ranking["TAXA_APROV_ANALISES_FMT"] = ranking["TAXA_APROV_ANALISES"].map(lambda v: f"{v:.1f}%")
ranking["TAXA_VENDAS_ANALISES_FMT"] = ranking["TAXA_VENDAS_ANALISES"].map(lambda v: f"{v:.1f}%")

ranking_exibe = ranking[
    [
        "POSICAO",
        "CORRETOR",
        "VGV_FMT",
        "VENDAS",
        "ANALISES",
        "APROVACOES",
        "TAXA_APROV_ANALISES_FMT",
        "TAXA_VENDAS_ANALISES_FMT",
    ]
].rename(
    columns={
        "POSICAO": "POSIÇÃO",
        "CORRETOR": "CORRETOR",
        "VGV_FMT": "VGV",
        "VENDAS": "VENDAS",
        "ANALISES": "ANÁLISES",
        "APROVACOES": "APROVAÇÕES",
        "TAXA_APROV_ANALISES_FMT": "TAXA_APROV_ANALISES",
        "TAXA_VENDAS_ANALISES_FMT": "TAXA_VENDAS_ANALISES",
    }
)

# ---------------------------------------------------------
# EXIBIÇÃO DA TABELA
# ---------------------------------------------------------
st.markdown("### 📊 Tabela detalhada do ranking por corretor")

st.dataframe(
    ranking_exibe,
    use_container_width=True,
    hide_index=True,
)

# ---------------------------------------------------------
# GRÁFICO DE BARRAS – VGV POR CORRETOR
# ---------------------------------------------------------
chart_data = ranking.copy()

chart = (
    alt.Chart(chart_data)
    .mark_bar()
    .encode(
        x=alt.X("CORRETOR:N", sort="-y", title="Corretor"),
        y=alt.Y("VGV:Q", title="VGV"),
        tooltip=[
            alt.Tooltip("CORRETOR:N", title="Corretor"),
            alt.Tooltip("VGV:Q", title="VGV", format=",.2f"),
            alt.Tooltip("VENDAS:Q", title="Vendas"),
            alt.Tooltip("ANALISES:Q", title="Análises"),
            alt.Tooltip("APROVACOES:Q", title="Aprovações"),
            alt.Tooltip("TAXA_APROV_ANALISES:Q", title="% Aprov./Análises", format=".1f"),
            alt.Tooltip("TAXA_VENDAS_ANALISES:Q", title="% Vendas/Análises", format=".1f"),
        ],
    )
    .properties(height=500)
)

st.altair_chart(chart, use_container_width=True)

st.markdown(
    "<hr><p style='text-align:center;color:#666;'>"
    "Ranking por corretor baseado em análises, aprovações, vendas (1 por cliente) e VGV, "
    "já considerando que clientes com último status DESISTIU têm suas vendas anuladas."
    "</p>",
    unsafe_allow_html=True,
)
