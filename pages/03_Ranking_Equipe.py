import streamlit as st
import pandas as pd
import altair as alt
from datetime import timedelta, datetime

if "logado" not in st.session_state or not st.session_state.logado:
    st.warning("🔒 Acesso restrito. Faça login para continuar.")
    st.stop()

st.set_page_config(
    page_title="Ranking de Corretores – Kratos",
    page_icon="🏆",
    layout="wide",
)

try:
    st.sidebar.image("logo_kratos.png", use_container_width=True)
except Exception:
    pass

st.title("🏆 Ranking de Análises por Corretor")

SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID_ANALISES = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ANALISES}"


def limpar_para_data(serie: pd.Series) -> pd.Series:
    dt = pd.to_datetime(serie, dayfirst=True, errors="coerce")
    return dt.dt.date


def mes_ano_ptbr_para_date(valor: str):
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

    try:
        partes = s.split()
        mes_txt = partes[0]
        ano = int(partes[-1])
        mes_num = meses.get(mes_txt)
        if mes_num is None:
            return pd.NaT
        return datetime(ano, mes_num, 1).date()
    except Exception:
        return pd.NaT


def carregar_dados() -> pd.DataFrame:
    df = pd.read_csv(CSV_URL)
    df.columns = [c.strip().upper() for c in df.columns]

    if "DATA" in df.columns:
        df["DIA"] = limpar_para_data(df["DATA"])
    elif "DIA" in df.columns:
        df["DIA"] = limpar_para_data(df["DIA"])
    else:
        df["DIA"] = pd.NaT

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
        df["DATA_BASE_LABEL"] = base_raw.str.lower().str.title()
        df["DATA_BASE"] = base_raw.apply(mes_ano_ptbr_para_date)

        if df["DATA_BASE"].dropna().empty:
            df["DATA_BASE"] = df["DIA"]
            df["DATA_BASE_LABEL"] = df["DIA"].apply(
                lambda d: d.strftime("%m/%Y") if pd.notnull(d) else ""
            )
    else:
        df["DATA_BASE"] = df["DIA"]
        df["DATA_BASE_LABEL"] = df["DIA"].apply(
            lambda d: d.strftime("%m/%Y") if pd.notnull(d) else ""
        )

    if "CORRETOR" in df.columns:
        df["CORRETOR"] = (
            df["CORRETOR"]
            .fillna("NÃO INFORMADO")
            .astype(str)
            .str.upper()
            .str.strip()
        )
    else:
        df["CORRETOR"] = "NÃO INFORMADO"

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

    return df


df = carregar_dados()

if df.empty:
    st.error("Erro ao carregar planilha.")
    st.stop()

dias_validos = df["DIA"].dropna()

if dias_validos.empty:
    st.error("Não foi possível identificar datas válidas na planilha.")
    st.stop()

st.sidebar.title("Filtros 🔎")

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

    if isinstance(periodo, (tuple, list)) and len(periodo) == 2:
        data_ini, data_fim = periodo
    else:
        data_ini, data_fim = data_ini_default, data_max
else:
    tipo_periodo = "DATA_BASE"

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

if tipo_periodo == "DIA":
    df_ref = df[
        (df["DIA"].notna()) &
        (df["DIA"] >= data_ini) &
        (df["DIA"] <= data_fim)
    ].copy()
else:
    df_ref = df[df["DATA_BASE_LABEL"].isin(bases_selecionadas)].copy()

    dias_sel = df_ref["DIA"].dropna()
    if not dias_sel.empty:
        data_ini = dias_sel.min()
        data_fim = dias_sel.max()
    else:
        data_ini = dias_validos.min()
        data_fim = dias_validos.max()

registros_ref = len(df_ref)

if tipo_periodo == "DIA":
    periodo_str = f"{data_ini.strftime('%d/%m/%Y')} até {data_fim.strftime('%d/%m/%Y')}"
else:
    if len(bases_selecionadas) == 1:
        periodo_str = bases_selecionadas[0]
    else:
        periodo_str = f"{bases_selecionadas[0]} até {bases_selecionadas[-1]}"

st.caption(
    f"Período: {periodo_str} • "
    f"Registros considerados: {registros_ref}"
)

if df_ref.empty:
    st.warning("Sem registros para os filtros selecionados.")
    st.stop()

df_analises = df_ref[df_ref["STATUS_BASE"].isin(["EM ANÁLISE", "REANÁLISE"])].copy()

ranking = (
    df_analises.groupby("CORRETOR")
    .size()
    .rename("ANALISES")
    .reset_index()
)

if ranking.empty:
    st.warning("Não há análises no período selecionado.")
    st.stop()

ranking["ANALISES"] = ranking["ANALISES"].astype(int)

ranking = ranking.sort_values(
    by=["ANALISES", "CORRETOR"],
    ascending=[False, True],
).reset_index(drop=True)

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

ranking_exibe = ranking[
    ["POSICAO", "CORRETOR", "ANALISES"]
].rename(
    columns={
        "POSICAO": "POSIÇÃO",
        "CORRETOR": "CORRETOR",
        "ANALISES": "ANÁLISES",
    }
)

st.markdown("### 📊 Ranking de análises por corretor")
st.dataframe(ranking_exibe, use_container_width=True, hide_index=True)

st.markdown("### 📈 Análises por corretor")

chart = (
    alt.Chart(ranking)
    .mark_bar()
    .encode(
        x=alt.X("CORRETOR:N", sort="-y", title="Corretor"),
        y=alt.Y("ANALISES:Q", title="Análises"),
        tooltip=[
            alt.Tooltip("CORRETOR:N", title="Corretor"),
            alt.Tooltip("ANALISES:Q", title="Análises"),
        ],
    )
    .properties(height=450)
)

st.altair_chart(chart, use_container_width=True)

st.markdown(
    "<hr><p style='text-align:center;color:#666;'>"
    "Ranking por corretor baseado somente na quantidade de análises "
    "(EM ANÁLISE + REANÁLISE) dentro do período selecionado."
    "</p>",
    unsafe_allow_html=True,
)