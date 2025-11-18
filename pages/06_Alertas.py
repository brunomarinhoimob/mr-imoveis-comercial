import streamlit as st
import pandas as pd
from datetime import timedelta, date

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Alertas – Corretores sem Análises",
    page_icon="🔴",
    layout="wide",
)

st.title("🔴 Corretores sem análises nos últimos 3 dias (janela de 30 dias)")

# ---------------------------------------------------------
# CONFIG: LINK DA PLANILHA  (MESMO DO APP PRINCIPAL)
# ---------------------------------------------------------
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID_ANALISES = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ANALISES}"

# ---------------------------------------------------------
# FUNÇÃO AUXILIAR PARA LIMPAR DATA
# ---------------------------------------------------------
def limpar_para_data(serie):
    dt = pd.to_datetime(serie, dayfirst=True, errors="coerce")
    return dt.dt.date

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

    # SITUAÇÃO BASE
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

    return df


df = carregar_dados()

if df.empty:
    st.error("Não foi possível carregar dados da planilha. Verifique o link/gid.")
    st.stop()

# ---------------------------------------------------------
# SIDEBAR – FILTRO DE EQUIPE
# ---------------------------------------------------------
st.sidebar.title("Filtros 🔎")

lista_equipes = sorted(df["EQUIPE"].dropna().unique())
equipe_sel = st.sidebar.selectbox("Equipe", ["Todas"] + lista_equipes)

# Aplica filtro de equipe na base inteira
if equipe_sel != "Todas":
    df = df[df["EQUIPE"] == equipe_sel]

if df.empty:
    st.warning("Não há registros para a equipe selecionada.")
    st.stop()

# ---------------------------------------------------------
# LÓGICA DO ALERTA (3 DIAS SEM ANÁLISE, DENTRO DA JANELA DE 30 DIAS)
# ---------------------------------------------------------

# Considera apenas registros de ANÁLISE / REANÁLISE
df_analise_base = df[df["STATUS_BASE"].isin(["EM ANÁLISE", "REANÁLISE"])].copy()

if df_analise_base.empty or df_analise_base["DIA"].isna().all():
    if equipe_sel == "Todas":
        st.info("Ainda não há análises registradas para calcular alertas.")
    else:
        st.info(f"A equipe **{equipe_sel}** não possui análises registradas para cálculo de alertas.")
    st.stop()

# Converte a data de análise
dt_analise = pd.to_datetime(df_analise_base["DIA"], errors="coerce")
df_analise_base = df_analise_base.assign(DT_ANALISE=dt_analise)

# Data de referência = última data de análise da base filtrada
data_ref_ts = df_analise_base["DT_ANALISE"].max()
if pd.isna(data_ref_ts):
    st.info("Não foi possível identificar a data de referência na base.")
    st.stop()

data_ref = data_ref_ts.date()
data_inicio_janela = data_ref - timedelta(days=30)

# Mantém somente análises dentro dos últimos 30 dias
df_analise_30 = df_analise_base[
    df_analise_base["DT_ANALISE"].dt.date >= data_inicio_janela
].copy()

if df_analise_30.empty:
    msg_base = (
        f"Não há análises nos últimos 30 dias (data de referência: "
        f"{data_ref.strftime('%d/%m/%Y')})."
    )
    if equipe_sel != "Todas":
        msg_base = f"A equipe **{equipe_sel}** não possui análises nos últimos 30 dias."
    st.info(msg_base)
    st.stop()

# Última análise (dentro da janela de 30 dias) por corretor
ultima_analise_corretor = (
    df_analise_30.dropna(subset=["DT_ANALISE"])
    .groupby("CORRETOR", as_index=False)["DT_ANALISE"]
    .max()
)

# Lista de todos os corretores da base (já filtrada pela equipe, se tiver)
corretores_todos = sorted(df["CORRETOR"].dropna().unique().tolist())

registros_alerta = []

for corr in corretores_todos:
    linha = ultima_analise_corretor[ultima_analise_corretor["CORRETOR"] == corr]

    if linha.empty:
        # esse corretor NÃO teve análise nos últimos 30 dias
        # ou nunca analisou – fica de fora do alerta
        continue

    ultima_dt = linha["DT_ANALISE"].iloc[0].date()
    dias_sem = (data_ref - ultima_dt).days

    # entra no alerta apenas se estiver há 3 dias ou mais sem análise
    if dias_sem >= 3:
        registros_alerta.append(
            {
                "CORRETOR": corr,
                "ÚLTIMA ANÁLISE": ultima_dt.strftime("%d/%m/%Y"),
                "DIAS SEM ANÁLISE (janela 30d)": dias_sem,
            }
        )

# ---------------------------------------------------------
# EXIBIÇÃO
# ---------------------------------------------------------
if equipe_sel == "Todas":
    sub_titulo = ""
else:
    sub_titulo = f" – Equipe **{equipe_sel}**"

st.caption(
    f"Data de referência considerada: **{data_ref.strftime('%d/%m/%Y')}**. "
    f"A janela de análise é sempre os **últimos 30 dias**{sub_titulo}. "
    "Entram aqui somente corretores que estão há **3 dias ou mais** sem subir análises, "
    "mas que ainda tiveram alguma análise dentro desses 30 dias."
)

if not registros_alerta:
    if equipe_sel == "Todas":
        st.success(
            "✅ Nenhum corretor está há 3 dias ou mais sem análises dentro da janela dos últimos 30 dias."
        )
    else:
        st.success(
            f"✅ Nenhum corretor da equipe **{equipe_sel}** está há 3 dias ou mais "
            "sem análises dentro da janela dos últimos 30 dias."
        )
else:
    df_alerta = pd.DataFrame(registros_alerta).sort_values(
        "DIAS SEM ANÁLISE (janela 30d)", ascending=False
    )

    # Destaque em vermelho na coluna de dias
    def colorir_dias(val):
        return "color: #f97373; font-weight: bold;"

    st.dataframe(
        df_alerta.style.applymap(
            colorir_dias, subset=["DIAS SEM ANÁLISE (janela 30d)"]
        ),
        use_container_width=True,
        hide_index=True,
    )
